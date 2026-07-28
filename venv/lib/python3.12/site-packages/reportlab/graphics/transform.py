'''functions for 2D affine transformations'''
__all__ = (
    'nullTransform',
    'translate',
    'scale',
    'rotate',
    'skewX',
    'skewY',
    'mmult',
    'inverse',
    'zTransformPoint',
    'transformPoint',
    'transformPoints',
    'zTransformPoints',
    )
from math import cos, sin, tan, radians

# constructors for matrices:
def nullTransform():
    return (1, 0, 0, 1, 0, 0)

def translate(dx, dy):
    return (1, 0, 0, 1, dx, dy)

def scale(sx, sy):
    return (sx, 0, 0, sy, 0, 0)

def rotate(angle):
    a = radians(angle)
    sina = sin(a)
    cosa = cos(a)
    return (cosa, sina, -sina, cosa, 0, 0)

def skewX(angle):
    return (1, 0, tan(radians(angle)), 1, 0, 0)

def skewY(angle):
    return (1, tan(radians(angle)), 0, 1, 0, 0)

def mmult(A, B):
    "A postmultiplied by B"
    # I checked this RGB
    # [a0 a2 a4]    [b0 b2 b4]
    # [a1 a3 a5] *  [b1 b3 b5]
    # [      1 ]    [      1 ]
    #
    return (A[0]*B[0] + A[2]*B[1],
            A[1]*B[0] + A[3]*B[1],
            A[0]*B[2] + A[2]*B[3],
            A[1]*B[2] + A[3]*B[3],
            A[0]*B[4] + A[2]*B[5] + A[4],
            A[1]*B[4] + A[3]*B[5] + A[5])

def inverse(A):
    "For A affine 2D represented as 6vec return 6vec version of A**(-1)"
    # I checked this RGB
    det = float(A[0]*A[3] - A[2]*A[1])
    R = [A[3]/det, -A[1]/det, -A[2]/det, A[0]/det]
    return tuple(R+[-R[0]*A[4]-R[2]*A[5],-R[1]*A[4]-R[3]*A[5]])

def zTransformPoint(A,v):
    "Apply the homogenous part of atransformation a to vector v --> A*v"
    return (A[0]*v[0]+A[2]*v[1],A[1]*v[0]+A[3]*v[1])

def transformPoint(A,v):
    "Apply transformation a to vector v --> A*v"
    return (A[0]*v[0]+A[2]*v[1]+A[4],A[1]*v[0]+A[3]*v[1]+A[5])

def transformPoints(matrix, V):
    r = [transformPoint(matrix,v) for v in V]
    if isinstance(V,tuple): r = tuple(r)
    return r

def zTransformPoints(matrix, V):
    return list(map(lambda x,matrix=matrix: zTransformPoint(matrix,x), V))
