# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Pure Python SM4 (GB/T 32907-2016) block cipher — fallback for the Aisino envelope.

``cryptography`` only exposes ``algorithms.SM4`` when it is built against an
OpenSSL that carries the SM4 cipher, which is not the case on every deployment
(and not before ``cryptography`` 35). The envelope in :mod:`sm4_envelope` needs
SM4/ECB regardless, so it falls back here.

Single block (16 bytes) in, single block out. ECB chaining and PKCS5 padding
stay in :mod:`sm4_envelope`; this module is the raw primitive only.
"""

SBOX = bytes.fromhex(
    'd690e9fecce13db716b614c228fb2c05'
    '2b679a762abe04c3aa44132649860699'
    '9c4250f491ef987a33540b43edcfac62'
    'e4b31ca9c908e89580df94fa758f3fa6'
    '4707a7fcf37317ba83593c19e6854fa8'
    '686b81b27164da8bf8eb0f4b70569d35'
    '1e240e5e6358d1a225227c3b01217887'
    'd40046579fd327524c3602e7a0c4c89e'
    'eabf8ad240c738b5a3f7f2cef96115a1'
    'e0ae5da49b341a55ad933230f58cb1e3'
    '1df6e22e8266ca60c02923ab0d534e6f'
    'd5db3745defd8e2f03ff6a726d6c5b51'
    '8d1baf92bbddbc7f11d95c411f105ad8'
    '0ac13188a5cd7bbd2d74d012b8e5b4b0'
    '8969974a0c96777e65b9f109c56ec684'
    '18f07dec3adc4d2079ee5f3ed7cb3948'
)

FK = (0xa3b1bac6, 0x56aa3350, 0x677d9197, 0xb27022dc)

CK = tuple(
    ((4 * i + 0) * 7 % 256) << 24
    | ((4 * i + 1) * 7 % 256) << 16
    | ((4 * i + 2) * 7 % 256) << 8
    | ((4 * i + 3) * 7 % 256)
    for i in range(32)
)

MASK = 0xffffffff


def _rotl(x, n):
    return ((x << n) | (x >> (32 - n))) & MASK


def _tau(a):
    """Non-linear layer: S-box applied to each of the four bytes."""
    return (
        SBOX[(a >> 24) & 0xff] << 24
        | SBOX[(a >> 16) & 0xff] << 16
        | SBOX[(a >> 8) & 0xff] << 8
        | SBOX[a & 0xff]
    )


def _t(a):
    """Round function T = L(tau(a)), L(B) = B ^ B<<<2 ^ B<<<10 ^ B<<<18 ^ B<<<24."""
    b = _tau(a)
    return b ^ _rotl(b, 2) ^ _rotl(b, 10) ^ _rotl(b, 18) ^ _rotl(b, 24)


def _t_prime(a):
    """Key-schedule function T' = L'(tau(a)), L'(B) = B ^ B<<<13 ^ B<<<23."""
    b = _tau(a)
    return b ^ _rotl(b, 13) ^ _rotl(b, 23)


def _words(data):
    return [int.from_bytes(data[i:i + 4], 'big') for i in range(0, len(data), 4)]


def expand_key(key):
    """Expand a 16-byte key into the 32 round keys."""
    if len(key) != 16:
        raise ValueError(f'SM4 needs a 128-bit key, got {len(key) * 8} bits')
    k = [w ^ f for w, f in zip(_words(key), FK)]
    round_keys = []
    for i in range(32):
        k.append(k[i] ^ _t_prime(k[i + 1] ^ k[i + 2] ^ k[i + 3] ^ CK[i]))
        round_keys.append(k[i + 4])
    return round_keys


def _crypt_block(block, round_keys):
    if len(block) != 16:
        raise ValueError(f'SM4 block must be 16 bytes, got {len(block)}')
    x = _words(block)
    for rk in round_keys:
        x.append(x[-4] ^ _t(x[-3] ^ x[-2] ^ x[-1] ^ rk))
    return b''.join(w.to_bytes(4, 'big') for w in reversed(x[-4:]))


def encrypt_block(block, key):
    return _crypt_block(block, expand_key(key))


def decrypt_block(block, key):
    return _crypt_block(block, expand_key(key)[::-1])


def encrypt_ecb(data, key):
    """ECB encrypt pre-padded data."""
    round_keys = expand_key(key)
    return b''.join(_crypt_block(data[i:i + 16], round_keys) for i in range(0, len(data), 16))


def decrypt_ecb(data, key):
    """ECB decrypt; padding is the caller's problem."""
    round_keys = expand_key(key)[::-1]
    return b''.join(_crypt_block(data[i:i + 16], round_keys) for i in range(0, len(data), 16))
