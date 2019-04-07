# ETCImagePlugin for Pillow

## What is this?

This is a work in progress (though almost functionally complete) custom plugin for the Python Library [Pillow](https://github.com/python-pillow/Pillow) that enables the decoding of files compressed by the [ETC (Ericsson Texture Compression) algorithm](https://en.wikipedia.org/wiki/Ericsson_Texture_Compression). It is able to decode ETC compressed files from passed byte data, as well as from .pkm files. 

## Why is this useful?

In conjunction with [UnityPack](https://github.com/HearthSim/UnityPack), this can be used to extract various assets from an Android Unity game, e.g. Shadowverse.

## What can it do so far?

As of now, it can decode RGB and RGBA textures encoded with ETC1 and ETC2. It cannot decode R , RG, sRGB, or sRGBA textures.

## How do I use it?

Just copy this script into your project and import it, then use Pillow as normal.
