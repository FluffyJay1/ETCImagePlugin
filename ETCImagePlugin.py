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
	
IMPLEMENTED_FORMATS = (
	TextureType.ETC1_RGB_NO_MIPMAPS,
)

def read_etc_header(data):
		#small PKM header, just hope it's not KTX
		#big endian
		#0-3 = magic number
		#4-5 = version
		#6-7 = texture type, most likely ETC1_RGB_NO_MIPMAPS = 0
		#8-9 = width
		#10-11 = height
		#12-13 = active width
		#14-15 = active 
		if data[:4] != b"PKM ":
			raise SyntaxError("not a PKM file")

		if data[4:6] != b"10":
			raise NotImplementedError("ETC Version 2 not supported")

		texture_type = data[7] # not enough texture types to need both bytes
		if texture_type not in IMPLEMENTED_FORMATS:
			raise NotImplementedError("Texture type " + texture_type + " not supported")
			
		width = struct.unpack(">h", data[8:10])[0]
		height = struct.unpack(">h", data[10:12])[0]
		active_width = struct.unpack(">h", data[12:14])[0]
		active_height = struct.unpack(">h", data[14:16])[0]
		return (texture_type, width, height, active_width, active_height)

class ETCImageFile(ImageFile.ImageFile):

	format = "ETC"
	format_description = "Ericsson Compressed Texture"

	def _open(self):
		# check header
		header = self.fp.read(16)
		texture_type, width, height, active_width, active_height = read_etc_header(header)

		# size in pixels (width, height)
		self.size = active_width, active_height

		# mode setting
		self.mode = "RGB" #Only 8 bits per channel for ETC1

        # data descriptor
		self.tile = [
			("ETC", (0, 0) + self.size, 16, (width, height, active_width, active_height))
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

class ETCBlock:

	
	
	def __init__(self, bytedata):
		self.diffbit = bytedata[3] & 0b00000010 > 0 #30th bit from left
		self.flipbit = bytedata[3] & 0b00000001 > 0 #31st bit from left
		if self.diffbit:
			r1 = self.expand_to_byte(bytedata[0] >> 3, 5)
			r2 = self.expand_to_byte(self.clamp_bits((bytedata[0] >> 3) + self.get_signed_val(bytedata[0], 3), 5), 5)
			g1 = self.expand_to_byte(bytedata[1] >> 3, 5)
			g2 = self.expand_to_byte(self.clamp_bits((bytedata[1] >> 3) + self.get_signed_val(bytedata[1], 3), 5), 5)
			b1 = self.expand_to_byte(bytedata[2] >> 3, 5)
			b2 = self.expand_to_byte(self.clamp_bits((bytedata[2] >> 3) + self.get_signed_val(bytedata[2], 3), 5), 5)
			self.base = (r1, g1, b2), (r2, g2, b2)
		else:
			r1 = self.expand_to_byte(bytedata[0] >> 4, 4)
			r2 = self.expand_to_byte(bytedata[0], 4)
			g1 = self.expand_to_byte(bytedata[1] >> 4, 4)
			g2 = self.expand_to_byte(bytedata[1], 4)
			b1 = self.expand_to_byte(bytedata[2] >> 4, 4)
			b2 = self.expand_to_byte(bytedata[2], 4)
			self.base = (r1, g1, b1), (r2, g2, b2)
			
		self.table = bytedata[3] >> 5, self.mask_bits(bytedata[3] >> 2, 3)
		
		self.colors = [[(0, 0, 0) for v in range(0, 4)] for u in range(0, 4)]

		for i in range(0,8): #first 8 pixels from the right of the bits
			coords = self.pixel_to_coords(i)
			self.colors[coords[0]][coords[1]] = self.get_final_color_at_coords(coords, self.get_bit(bytedata[5], i), self.get_bit(bytedata[7], i))
			
		for i in range(0,8): #next 8 pixels from the right of the bits
			coords = self.pixel_to_coords(i + 8)
			self.colors[coords[0]][coords[1]] = self.get_final_color_at_coords(coords, self.get_bit(bytedata[4], i), self.get_bit(bytedata[6], i))
				
	def clamp_bits(self, byte, num_bits):
		if byte < 0:
			return 0
		elif byte > (1 << num_bits) - 1:
			return (1 << num_bits) - 1
		else:
			return int(byte)
	
	def mask_bits(self, byte, num_bits):
		return byte & ((1 << num_bits) - 1)

	def expand_to_byte(self, byte, num_bits):
		return self.mask_bits((self.mask_bits(byte, num_bits) >> (2 * num_bits - 8)) | (self.mask_bits(byte, num_bits) << (8 - num_bits)), 8)

	def get_signed_val(self, byte, num_bits):
		if byte & (1 << (num_bits - 1)) > 0: #if "first" bit is signed
			return self.mask_bits(byte, num_bits - 1) - (1 << (num_bits - 1)) #twos compliment
		else:
			return self.mask_bits(byte, num_bits - 1)
		
	#pixel index is from the right
	def pixel_to_coords(self, pixel_index):
		return (int(pixel_index/4), pixel_index % 4)
		
	def coords_to_pixel(self, coords):
		return coords[0] * 4 + coords[1]
		
	def get_bit(self, data, index):
		return (data >> index) & 1
		
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
				
	def get_final_color_at_coords(self, coords, msb, lsb):
		subblock = self.get_subblock_at_coords(coords)
		base = self.base[subblock]
		table = self.table[subblock]
		final_index = 0
		if msb == 0 or lsb == 0:
			if msb > 0:
				final_index = 1
			elif lsb > 0:
				final_index = 3
			else:
				final_index = 2
				
		r = self.clamp_bits(base[0] + INTENSITY_MODIFIERS[table][final_index], 8)
		g = self.clamp_bits(base[1] + INTENSITY_MODIFIERS[table][final_index], 8)
		b = self.clamp_bits(base[2] + INTENSITY_MODIFIERS[table][final_index], 8)
		return (r, g, b)
		
class ETCDecoder(ImageFile.PyDecoder):
	load_mode = False
	
	#if init gets called, we know decode will be called from load(), else it's from fromBytes()
	def init(self, args):
		self.init_from_header(args)
		self.load_mode = True
		
	def decode(self, buffer):
		if self.load_mode:
			for i in range(0, int((len(buffer) + 7)/8)):
				self.decode_block(buffer[(i * 8):(i * 8 + 8)])
			retbytes = len(buffer)
			if self.curr_ind >= self.block_dim[0] * self.block_dim[1]:
				retbytes = -1
				self.write_blocks_to_image()
				
			return (retbytes, 0)
		else :
			self.init_from_header((int((self.im.size[0] + 3) / 4) * 4, int((self.im.size[1] + 3) / 4) * 4, self.im.size[0], self.im.size[1]))
			ptr = 0
			for v in range(0,self.block_dim[1]):
				for u in range(0, self.block_dim[0]):
					self.decode_block(buffer[ptr:(ptr + 8)])
					ptr += 8
			
			self.write_blocks_to_image()
			return (-1, 0)
		
	def decode_block(self, data):
		coord = self.ind_to_coord(self.curr_ind)
		self.blocks[coord[0]][coord[1]] = ETCBlock(data)
		self.curr_ind += 1
		
	def init_from_header(self, args):
		self.block_dim = (int(args[0] / 4), int(args[1] / 4))
		self.blocks = [[object() for v in range(0,self.block_dim[1])] for u in range(0, self.block_dim[0])]
		self.active_dim = args[2:4]
		self.curr_ind = 0
		
	def ind_to_coord(self, index):
		return (index % self.block_dim[0], int(index / self.block_dim[0]))
		
	def write_blocks_to_image(self):
		data = bytearray()
		for v in range(0, self.block_dim[1]):
			for y in range(0, 4):
				if y + v * 4 >= self.active_dim[1]:
					break
				
				for u in range(0, self.block_dim[0]):
					for x in range(0, 4):
						if x + u * 4 >= self.active_dim[0]:
							break
						data.extend(self.blocks[u][v].colors[x][y])
		
		self.set_as_raw(bytes(data))

Image.register_open(ETCImageFile.format, ETCImageFile)
Image.register_extension(ETCImageFile.format, ".pkm")
Image.register_extension(ETCImageFile.format, ".ktx")
Image.register_decoder("ETC", ETCDecoder)