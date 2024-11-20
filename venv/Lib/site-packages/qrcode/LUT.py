# Store all kinds of lookup table.


# # generate rsPoly lookup table.

# from qrcode import base

# def create_bytes(rs_blocks):
#     for r in range(len(rs_blocks)):
#         dcCount = rs_blocks[r].data_count
#         ecCount = rs_blocks[r].total_count - dcCount
#         rsPoly = base.Polynomial([1], 0)
#         for i in range(ecCount):
#             rsPoly = rsPoly * base.Polynomial([1, base.gexp(i)], 0)
#         return ecCount, rsPoly

# rsPoly_LUT = {}
# for version in range(1,41):
#     for error_correction in range(4):
#         rs_blocks_list = base.rs_blocks(version, error_correction)
#         ecCount, rsPoly = create_bytes(rs_blocks_list)
#         rsPoly_LUT[ecCount]=rsPoly.num
# print(rsPoly_LUT)

# Result. Usage: input: ecCount, output: Polynomial.num
# e.g. rsPoly = base.Polynomial(LUT.rsPoly_LUT[ecCount], 0)
rsPoly_LUT = {
    7:  [1, 127, 122, 154, 164, 11, 68, 117],
    10: [1, 216, 194, 159, 111, 199, 94, 95, 113, 157, 193],
    13: [1, 137, 73, 227, 17, 177, 17, 52, 13, 46, 43, 83, 132, 120],
    15: [1, 29, 196, 111, 163, 112, 74, 10, 105, 105, 139, 132, 151,
        32, 134, 26],
    16: [1, 59, 13, 104, 189, 68, 209, 30, 8, 163, 65, 41, 229, 98, 50, 36, 59],
    17: [1, 119, 66, 83, 120, 119, 22, 197, 83, 249, 41, 143, 134, 85, 53, 125,
        99, 79],
    18: [1, 239, 251, 183, 113, 149, 175, 199, 215, 240, 220, 73, 82, 173, 75,
        32, 67, 217, 146],
    20: [1, 152, 185, 240, 5, 111, 99, 6, 220, 112, 150, 69, 36, 187, 22, 228,
        198, 121, 121, 165, 174],
    22: [1, 89, 179, 131, 176, 182, 244, 19, 189, 69, 40, 28, 137, 29, 123, 67,
        253, 86, 218, 230, 26, 145, 245],
    24: [1, 122, 118, 169, 70, 178, 237, 216, 102, 115, 150, 229, 73, 130, 72,
        61, 43, 206, 1, 237, 247, 127, 217, 144, 117],
    26: [1, 246, 51, 183, 4, 136, 98, 199, 152, 77, 56, 206, 24, 145, 40, 209,
        117, 233, 42, 135, 68, 70, 144, 146, 77, 43, 94],
    28: [1, 252, 9, 28, 13, 18, 251, 208, 150, 103, 174, 100, 41, 167, 12, 247,
        56, 117, 119, 233, 127, 181, 100, 121, 147, 176, 74, 58, 197],
    30: [1, 212, 246, 77, 73, 195, 192, 75, 98, 5, 70, 103, 177, 22, 217, 138,
        51, 181, 246, 72, 25, 18, 46, 228, 74, 216, 195, 11, 106, 130, 150]
              }
