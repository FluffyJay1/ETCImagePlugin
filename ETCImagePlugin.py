from enum import IntEnum
from PIL import Image, ImageFile
import string
import struct

class TextureType(IntEnum):
	ETC1_RGB_NO_MIPMAPS = 0,
	ETC2PACKAGE_RGB_NO_MIPMAPS = 1,
	
	ETC2PACKAGE_RGBA_NO_MIPMAPS = 3,
	ETC2PACKAGE_RGBA1_NO_MIPMAPS = 4,
	ETC2PACKAGE_R_NO_MIPMAPS = 5,
	ETC2PACKAGE_RG_NO_MIPMAPS = 6,
	ETC2PACKAGE_R_SIGNED_NO_MIPMAPS = 7,
	ETC2PACKAGE_RG_SIGNED_NO_MIPMAPS = 8
	
class GLFormat(IntEnum):
	GL_R = 0x1903,
	GL_RG = 0x8227,
	GL_RGB = 0x1907,
	GL_RGBA = 0x1908,
	GL_SRGB = 0x8C40,
	GL_SRGB8 = 0x8C41,
	GL_SRGB8_ALPHA8 = 0x8C43,
	GL_ETC1_RGB8_OES = 0x8d64,
	GL_COMPRESSED_R11_EAC = 0x9270,
	GL_COMPRESSED_SIGNED_R11_EAC = 0x9271,
	GL_COMPRESSED_RG11_EAC = 0x9272,
	GL_COMPRESSED_SIGNED_RG11_EAC = 0x9273,
	GL_COMPRESSED_RGB8_ETC2 = 0x9274,
	GL_COMPRESSED_SRGB8_ETC2 = 0x9275,
	GL_COMPRESSED_RGB8_PUNCHTHROUGH_ALPHA1_ETC2 = 0x9276,
	GL_COMPRESSED_SRGB8_PUNCHTHROUGH_ALPHA1_ETC2 = 0x9277,
	GL_COMPRESSED_RGBA8_ETC2_EAC = 0x9278,
	GL_COMPRESSED_SRGB8_ALPHA8_ETC2_EAC = 0x9279
	
class Modes(IntEnum):
	INDIV = 0,
	DIFF = 1,
	T = 2,
	H = 3,
	PLANAR = 4
	
IMPLEMENTED_FORMATS = (
	TextureType.ETC1_RGB_NO_MIPMAPS,
	TextureType.ETC2PACKAGE_RGB_NO_MIPMAPS,
	TextureType.ETC2PACKAGE_RGBA_NO_MIPMAPS,
	TextureType.ETC2PACKAGE_RGBA1_NO_MIPMAPS
)

def read_etc_header(data):
		if data[0:12] == [0xAB, 0x4B, 0x54, 0x58, 0x20, 0x31, 0x31, 0xBB, 0x0D, 0x0A, 0x1A, 0x0A]:
			#KTX Header
			#0-11 = magic number
			#12-15 = endianness, should be 0x04030201
			#16-19 = glType, should be 0
			#20-23 = glTypeSize, should be 1
			#24-27 = glFormat, should be 0
			#28-31 = glInternalFormat, something from glformat enum
			#32-35 = glBaseInternalFormat, something from glformat enum
			#36-39 = pixelWidth
			#40-43 = pixelHeight
			#44-47 = pixelDepth, should be 0
			#48-51 = numberOfArrayElements, should be 0
			#52-55 = numberOfFaces, should be 1
			#56-59 = numberOfMipmapLevels, should be 1
			if struct.unpack(">i", data[12:16]) != 0x04030201:
				print("file endianness is weird")
				raise NotImplementedError("file endianness reversing not implemented yet!")
			#format unpacking
			internal_format = struct.unpack(">i", data[28:32])
			base_internal_format = struct.unpack(">i", data[32:36])
			if base_internal_format == GLFormat.GL_RGB: #RGB types
				if internal_format == GLFormat.GL_COMPRESSED_RGB8_ETC2:
					texture_type = TextureType.ETC2PACKAGE_RGB_NO_MIPMAPS
				elif internal_format == GLFormat.GL_ETC1_RGB8_OES:
					texture_type = TextureType.ETC1_RGB_NO_MIPMAPS
				else:
					print("texture type for internal format " + str(internal_format) + " cannot be determined!")
					raise NotImplementedError("file texture type not implemented yet!")
			elif base_internal_format == GLFormat.GL_RGBA: #RGBA types
				if internal_format == GLFormat.GL_COMPRESSED_RGBA8_ETC2_EAC:
					texture_type = TextureType.ETC2PACKAGE_RGBA_NO_MIPMAPS
				elif internal_format == GLFormat.GL_COMPRESSED_RGB8_PUNCHTHROUGH_ALPHA1_ETC2:
					texture_type = TextureType.ETC2PACKAGE_RGBA_NO_MIPMAPS
				else:
					print("texture type for internal format " + str(internal_format) + " cannot be determined!")
					raise NotImplementedError("file texture type not implemented yet!")
			else:
				print("texture type for internal format " + str(internal_format) + " cannot be determined!")
				raise NotImplementedError("file texture type not implemented yet!")
				
			#img dimensions CHECK THIS
			active_width = struct.unpack(">i", data[36:40])
			active_height = struct.unpack(">i", data[40:44])
			width = int((active_width + 3) / 4) * 4
			height = int((active_height + 3) / 4) * 4
		elif data[:4] == b"PKM ":
			#PKM Header
			#big endian
			#0-3 = magic number
			#4-5 = version
			#6-7 = texture type, from TextureType enum
			#8-9 = width
			#10-11 = height
			#12-13 = active width
			#14-15 = active height
			version = data[4:6] #potentially useful

			texture_type = data[7] # not enough texture types to need both bytes
			if texture_type not in IMPLEMENTED_FORMATS:
				raise NotImplementedError("Texture type " + texture_type + " not supported")
				
			width = struct.unpack(">h", data[8:10])[0]
			height = struct.unpack(">h", data[10:12])[0]
			active_width = struct.unpack(">h", data[12:14])[0]
			active_height = struct.unpack(">h", data[14:16])[0]
		else:
			raise SyntaxError("not a KTX or PKM file")
		return (texture_type, active_width, active_height)
		
class ETCImageFile(ImageFile.ImageFile):

	format = "ETC"
	format_description = "Ericsson Compressed Texture"

	def _open(self):
		# check header
		header = self.fp.read(16)
		texture_type, active_width, active_height = read_etc_header(header)

		# size in pixels (width, height)
		self.size = active_width, active_height

		# mode setting
		if texture_type == TextureType.ETC1_RGB_NO_MIPMAPS or texture_type == TextureType.ETC2PACKAGE_RGB_NO_MIPMAPS:
			self.mode = "RGB" #Only 8 bits per channel for ETC1
		elif texture_type == TextureType.ETC2PACKAGE_RGBA1_NO_MIPMAPS or texture_type == TextureType.ETC2PACKAGE_RGBA_NO_MIPMAPS:
			self.mode = "RGBA"

        # data descriptor
		self.tile = [
			("ETC", (0, 0) + self.size, 16, (texture_type, active_width, active_height))
		]
		
INTENSITY_MODIFIERS = [
	[-8, -2, 2, 8],			#0
	[-17, -5, 5, 17],		#1
	[-29, -9, 9, 29],		#2
	[-42, -13, 13, 42],		#3
	[-60, -18, 18, 60],		#4
	[-80, -24, 24, 80],		#4
	[-106, -33, 33, 106],	#6
	[-183, -47, 47, 183],	#7
]

DISTANCE_TABLE = [3, 6, 11, 16, 23, 32, 41, 64]

ALPHA_TABLE = [
[-3, -6, -9, -15, 2, 5, 8, 14],
[-3, -7, -10, -13, 2, 6, 9, 12],
[-2, -5, -8, -13, 1, 4, 7, 12],
[-2, -4, -6, -13, 1, 3, 5, 12],
[-3, -6, -8, -12, 2, 5, 7, 11],
[-3, -7, -9, -11, 2, 6, 8, 10],
[-4, -7, -8, -11, 3, 6, 7, 10],
[-3, -5, -8, -11, 2, 4, 7, 10],
[-2, -6, -8, -10, 1, 5, 7, 9],
[-2, -5, -8, -10, 1, 4, 7, 9],
[-2, -4, -8, -10, 1, 3, 7, 9],
[-2, -5, -7, -10, 1, 4, 6, 9],
[-3, -4, -7, -10, 2, 3, 6, 9],
[-1, -2, -3, -10, 0, 1, 2, 9],
[-4, -6, -8, -9, 3, 5, 7, 8],
[-3, -5, -7, -9, 2, 4, 6, 8]
]

##HELPER METHODS

def clamp(num, low, high):
	if num <= low:
		return low
	elif num >= high:
		return high
	else:
		return num
			
def clamp_bits(byte, num_bits):
	return clamp(int(byte), 0, (1 << num_bits) - 1)

def mask_bits(byte, num_bits):
	return byte & ((1 << num_bits) - 1)

def expand_to_byte(byte, num_bits):
	return mask_bits((mask_bits(byte, num_bits) >> (2 * num_bits - 8)) | (mask_bits(byte, num_bits) << (8 - num_bits)), 8)

def get_signed_val(byte, num_bits):
	if byte & (1 << (num_bits - 1)) > 0: #if "first" bit is signed
		return mask_bits(byte, num_bits - 1) - (1 << (num_bits - 1)) #twos compliment
	else:
		return mask_bits(byte, num_bits - 1)
	
#pixel index is from the right
def pixel_to_coords(pixel_index):
	return (int(pixel_index/4), pixel_index % 4)
	
def coords_to_pixel(coords):
	return coords[0] * 4 + coords[1]
	
def get_bit(data, index):
	return (data >> index) & 1
			
def modify_brightness(color, brightness):
	return (clamp(color[0] + brightness, 0, 255), clamp(color[1] + brightness, 0, 255), clamp(color[2] + brightness, 0, 255))
	
class ETCBlock: #potentially useful?
	pass
	

class ETCRGBBlock(ETCBlock):
	
	def __init__(self, bytedata, punchthrough):
		self.diffbit = bytedata[3] & 0b00000010 > 0 #30th bit from left
		self.flipbit = bytedata[3] & 0b00000001 > 0 #31st bit from left
		self.punchthrough = punchthrough
		if not punchthrough and not self.diffbit:
			self.mode = Modes.INDIV
			self.decode_indiv(bytedata[0] >> 4, bytedata[0],
								bytedata[1] >> 4, bytedata[1],
								bytedata[2] >> 4, bytedata[2])
		else:
			tempr2 = (bytedata[0] >> 3) + get_signed_val(bytedata[0], 3) #test for T
			if tempr2 < 0 or tempr2 > 31: #T mode
				self.mode = Modes.T
				self.decode_T((bytedata[0] >> 1 & 0b00001100) | mask_bits(bytedata[0], 2), #1
								bytedata[1] >> 4,
								bytedata[1],
								bytedata[2] >> 4, #2
								bytedata[2],
								bytedata[3] >> 4,
								(bytedata[3] >> 1 & 0b00000110) | bytedata[3] & 1) #d
			else:
				tempg2 = (bytedata[1] >> 3) + get_signed_val(bytedata[1], 3)
				if tempg2 < 0 or tempg2 > 31: #H mode
					self.mode = Modes.H
					
					r1 = mask_bits(bytedata[0] >> 3, 4)
					g1 =(mask_bits(bytedata[0], 3) << 1) | (bytedata[1] >> 4 & 1)
					b1 = (bytedata[1] & 0b00001000) | (bytedata[1] << 1 & 0b00000110) | (bytedata[2] >> 7)
					r2 = mask_bits(bytedata[2] >> 3, 4)
					g2 = (mask_bits(bytedata[2], 3) << 1) | (bytedata[3] >> 7)
					b2 = mask_bits(bytedata[3] >> 3, 4)

					dc = 0
					if (r1 << 8) + (g1 << 4) + b1 >= (r2 << 8) + (g2 << 4) + b2:
						dc = 1
						
					d_ind = (bytedata[3] & 0b00000100) | (bytedata[3] << 1 & 0b00000010) | dc
					self.decode_H(r1, g1, b1, r2, g2, b2, d_ind)
					
				else:
					tempb2 = (bytedata[2] >> 3) + get_signed_val(bytedata[2], 3)
					if tempb2 < 0 or tempb2 > 31: #Planar mode
						self.mode = Modes.PLANAR
						ro = bytedata[0] >> 1
						go = (bytedata[0] << 6 & 0b01000000) | mask_bits(bytedata[1] >> 1, 6)
						#have mercy
						bo = (bytedata[1] << 5 & 0b00100000) | (bytedata[2] & 0b00011000) | (bytedata[2] << 1 & 0b00000110) | (bytedata[3] >> 7)
						rh = (bytedata[3] >> 1 & 0b00111110) | (bytedata[3] & 1)
						gh = bytedata[4] >> 1
						bh = (bytedata[4] << 5 & 0b00100000) | mask_bits(bytedata[5] >> 3, 5)
						rv = (bytedata[5] << 3 & 0b00111000) | mask_bits(bytedata[6] >> 5, 3)
						gv = (bytedata[6] << 2 & 0b01111100) | mask_bits(bytedata[7] >> 6, 2)
						bv = mask_bits(bytedata[7], 6)
						
						self.decode_planar(ro, go, bo, rh, gh, bh, rv, gv, bv)
						
					else: #no overflow/underflowing values, just regular diff
						self.mode = Modes.DIFF
						r1 = expand_to_byte(bytedata[0] >> 3, 5)
						r2 = expand_to_byte(tempr2, 5)
						g1 = expand_to_byte(bytedata[1] >> 3, 5)
						g2 = expand_to_byte(tempg2, 5)
						b1 = expand_to_byte(bytedata[2] >> 3, 5)
						b2 = expand_to_byte(tempb2, 5)
						self.base = (r1, g1, b2), (r2, g2, b2)
						
		if self.mode == Modes.INDIV or self.mode == Modes.DIFF:
			self.table = bytedata[3] >> 5, mask_bits(bytedata[3] >> 2, 3)
		
		self.colors = [[(0, 0, 0) for v in range(0, 4)] for u in range(0, 4)]
		if self.punchthrough:
			self.alphas = [[255 for v in range(0, 4)] for u in range(0, 4)]

		if self.mode == Modes.PLANAR:
			for u in range(0, 4):
				for v in range(0, 4):
					self.colors[u][v] = self.get_final_color_at_coords((u, v), 0)
					if self.punchthrough:
						self.alphas[u][v] = self.get_alpha_at_coords((u, v), 0)
		else:
			for i in range(0,8): #first 8 pixels from the right of the bits
				coords = pixel_to_coords(i)
				ind = (get_bit(bytedata[5], i) << 1) | get_bit(bytedata[7], i)
				self.colors[coords[0]][coords[1]] = self.get_final_color_at_coords(coords, ind)
				if self.punchthrough:
					self.alphas[coords[0]][coords[1]] = self.get_alpha_at_coords(coords, ind)
				
			for i in range(0,8): #next 8 pixels from the right of the bits
				coords = pixel_to_coords(i + 8)
				ind = (get_bit(bytedata[4], i) << 1) | get_bit(bytedata[6], i)
				self.colors[coords[0]][coords[1]] = self.get_final_color_at_coords(coords, ind)
				if self.punchthrough:
					self.alphas[coords[0]][coords[1]] = self.get_alpha_at_coords(coords, ind)
				
	def decode_indiv(self, r1, r2, g1, g2, b1, b2):
		er1 = expand_to_byte(r1, 4)
		er2 = expand_to_byte(r2, 4)
		eg1 = expand_to_byte(g1, 4)
		eg2 = expand_to_byte(g2, 4)
		eb1 = expand_to_byte(b1, 4)
		eb2 = expand_to_byte(b2, 4)
		self.base = (er1, eg1, eb1), (er2, eg2, eb2)
		
	def decode_T(self, r1, g1, b1, r2, g2, b2, d_ind):
		er1 = expand_to_byte(r1, 4)
		eg1 = expand_to_byte(g1, 4)
		eb1 = expand_to_byte(b1, 4)
		er2 = expand_to_byte(r2, 4)
		eg2 = expand_to_byte(g2, 4)
		eb2 = expand_to_byte(b2, 4)
		
		distance = DISTANCE_TABLE[d_ind]
		paint0 = (er1, eg1, eb1)
		paint1 = modify_brightness((er2, eg2, eb2), distance)
		paint2 = (er2, eg2, eb2)
		paint3 = modify_brightness((er2, eg2, eb2), -distance)
		self.paint = (paint0, paint1, paint2, paint3)
		
	def decode_H(self, r1, g1, b1, r2, g2, b2, d_ind):
		er1 = expand_to_byte(r1, 4)
		eg1 = expand_to_byte(g1, 4)
		eb1 = expand_to_byte(b1, 4)
		er2 = expand_to_byte(r2, 4)
		eg2 = expand_to_byte(g2, 4)
		eb2 = expand_to_byte(b2, 4)
			
		distance = DISTANCE_TABLE[d_ind]
		
		paint0 = modify_brightness((er1, eg1, eb1), distance)
		paint1 = modify_brightness((er1, eg1, eb1), -distance)
		paint2 = modify_brightness((er2, eg2, eb2), distance)
		paint3 = modify_brightness((er2, eg2, eb2), -distance)
		self.paint = (paint0, paint1, paint2, paint3)
		
	def decode_planar(self, ro, go, bo, rh, gh, bh, rv, gv, bv):
		ero = expand_to_byte(ro, 6)
		ego = expand_to_byte(go, 7)
		ebo = expand_to_byte(bo, 6)
		erh = expand_to_byte(rh, 6)
		egh = expand_to_byte(gh, 7)
		ebh = expand_to_byte(bh, 6)
		erv = expand_to_byte(rv, 6)
		egv = expand_to_byte(gv, 7)
		ebv = expand_to_byte(bv, 6)
		
		self.o = (ero, ego, ebo)
		self.h = (erh, egh, ebh)
		self.v = (erv, egv, ebv)
				
	def get_subblock_at_coords(self, coords):
		if self.flipbit:
			if coords[1] > 1:
				return 1
			else:
				return 0
		else:
			if coords[0] > 1:
				return 1
			else:
				return 0
	
	def get_final_color_at_coords(self, coords, ind):
		if self.mode == Modes.PLANAR:
			color = [clamp_bits((coords[0] * (self.h[i] - self.o[i]) + coords[1] * (self.v[i] - self.o[i]) + 4 * self.o[i] + 2) >> 2, 8) for i in range(0, 3)]
			return tuple(color)
		elif self.mode == Modes.T or self.mode == Modes.H: #use paints
			msb = ind >> 1
			lsb = ind & 1
			if self.punchthrough and not self.diffbit:
				if msb > 0 and lsb == 0:
					return (0, 0, 0)

			return self.paint[ind]
		else: #use base + brightness
			subblock = self.get_subblock_at_coords(coords)
			base = self.base[subblock]
			table = self.table[subblock]
			final_index = 0
			msb = ind >> 1
			lsb = ind & 1
			if msb == 0 or lsb == 0:
				if msb > 0:
					final_index = 1
				elif lsb > 0:
					final_index = 3
				else:
					final_index = 2
			
			lum_mod = INTENSITY_MODIFIERS[table][final_index]
			if self.punchthrough and not self.diffbit:
				if msb > 0 and lsb == 0:
					return (0, 0, 0)
				elif msb == 0 and lsb == 0:
					lum_mod = 0 
					
			color = [clamp_bits(base[i] + lum_mod, 8) for i in range(0, 3)]
			return tuple(color)
			
	def get_alpha_at_coords(self, coords, ind):
		if self.mode == Modes.PLANAR:
			return 255
		else:
			msb = ind >> 1
			lsb = ind & 1
			'''
			if self.punchthrough and not self.diffbit and msb > 0 and lsb > 0: #i find this to work
				return 0
			'''
			if self.punchthrough and not self.diffbit and msb > 0 and lsb == 0: #listed by khronos group, they're lying
				return 0
			
			return 255
			
			
class ETCAlphaBlock(ETCBlock):
	
	def __init__(self, bytedata):
		self.base = bytedata[0]
		self.multiplier = bytedata[1] >> 4
		self.table_ind = mask_bits(bytedata[1], 4)
		self.alphas = [[0 for v in range(0, 4)] for u in range(0, 4)]
		offset = 7 #first bit from the right
		curr_byte = 2
		for i in range(0, 16):
			tab_ind = 0
			if offset < 2:
				tab_ind = mask_bits(bytedata[curr_byte] << (2 - offset), 3) | (bytedata[curr_byte + 1] >> 6 + offset)
			else:
				tab_ind = mask_bits(bytedata[curr_byte] >> offset - 2, 3)
				
			coord = pixel_to_coords(i)
			self.alphas[coord[0]][coord[1]] = clamp_bits(self.base + self.multiplier * ALPHA_TABLE[self.table_ind][tab_ind], 8)
				
			offset -= 3
			if offset < 0:
				offset += 8
				curr_byte += 1
				
			
class ETCDecoder(ImageFile.PyDecoder):
	
	#args: an instance of the ETCImagePlugin.TextureType enum
	def init(self, args):
		self.texture_type = args[0]
		if self.texture_type not in IMPLEMENTED_FORMATS:
			raise NotImplementedError("Texture type " + texture_type + " not supported")
		self.curr_ind = 0
		
	def decode(self, buffer):
		self.init_from_image()
		print(len(buffer))
		print(self.block_dim)
		if self.texture_type == TextureType.ETC2PACKAGE_RGBA_NO_MIPMAPS: #if need alpha blocks
			for i in range(0, int(len(buffer)/16)): #consume data until image complete or the buffer is expended
				self.decode_alpha_block(buffer[(i * 16):(i * 16 + 8)])
				self.decode_rgb_block(buffer[(i * 16 + 8):(i * 16 + 16)])
				self.curr_ind += 1
				if self.curr_ind >= self.block_dim[0] * self.block_dim[1]:
					break
				
			retbytes = int(len(buffer)/16) * 16
		else:
			for i in range(0, int(len(buffer)/8)):
				self.decode_rgb_block(buffer[(i * 8):(i * 8 + 8)])
				self.curr_ind += 1
				if self.curr_ind >= self.block_dim[0] * self.block_dim[1]:
					break
				
			retbytes = int(len(buffer)/8) * 8
		if self.curr_ind >= self.block_dim[0] * self.block_dim[1]:
			retbytes = -1
			self.write_blocks_to_image()
			
		err = 0
		if retbytes == 0:
			err = -1
		return (retbytes, err)
			
	def init_from_image(self):
		self.block_dim = (int((self.im.size[0] + 3) / 4), int((self.im.size[1] + 3) / 4))
		self.blocks_rgb = [[object() for v in range(0,self.block_dim[1])] for u in range(0, self.block_dim[0])]
		if self.texture_type == TextureType.ETC2PACKAGE_RGBA_NO_MIPMAPS: #if need alpha blocks
			self.blocks_alpha = [[object() for v in range(0,self.block_dim[1])] for u in range(0, self.block_dim[0])]
		
	def decode_rgb_block(self, data):
		coord = self.ind_to_coord(self.curr_ind)
		self.blocks_rgb[coord[0]][coord[1]] = ETCRGBBlock(data, self.texture_type == TextureType.ETC2PACKAGE_RGBA1_NO_MIPMAPS)
		
	def decode_alpha_block(self, data):
		coord = self.ind_to_coord(self.curr_ind)
		self.blocks_alpha[coord[0]][coord[1]] = ETCAlphaBlock(data)
		
		
		
	def ind_to_coord(self, index):
		return (index % self.block_dim[0], int(index / self.block_dim[0]))
		
	def write_blocks_to_image(self):
		data = bytearray()
		for v in range(0, self.block_dim[1]):
			for y in range(0, 4):
				if y + v * 4 >= self.im.size[1]:
					break
				
				for u in range(0, self.block_dim[0]):
					for x in range(0, 4):
						if x + u * 4 >= self.im.size[0]:
							break
						data.extend(self.blocks_rgb[u][v].colors[x][y])
						if self.texture_type == TextureType.ETC2PACKAGE_RGBA1_NO_MIPMAPS: #punchthrough
							data.append(self.blocks_rgb[u][v].alphas[x][y])
						elif self.texture_type == TextureType.ETC2PACKAGE_RGBA_NO_MIPMAPS: #alpha blocks
							data.append(self.blocks_alpha[u][v].alphas[x][y])
						
		print(self.texture_type)
		print(len(data))
		self.set_as_raw(bytes(data))

Image.register_open(ETCImageFile.format, ETCImageFile)
Image.register_extension(ETCImageFile.format, ".pkm")
Image.register_extension(ETCImageFile.format, ".ktx")
Image.register_decoder("ETC", ETCDecoder)