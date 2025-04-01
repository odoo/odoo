'''this code is derived from that used by svglib.''' 
__all__=('SvgPath',)
import re, copy
from math import acos, ceil, copysign, cos, degrees, fabs, hypot, radians, sin, sqrt
from .shapes import Group, mmult, rotate, translate, transformPoint, Path, FILL_EVEN_ODD, _CLOSEPATH, UserNode

def split_floats(op, min_num, value):
    """Split `value`, a list of numbers as a string, to a list of float numbers.

    Also optionally insert a `l` or `L` operation depending on the operation
    and the length of values.
    Example: with op='m' and value='10,20 30,40,' the returned value will be
             ['m', [10.0, 20.0], 'l', [30.0, 40.0]]
    """
    floats = [float(seq) for seq in re.findall(r'(-?\d*\.?\d*(?:[eE][+-]?\d+)?)', value) if seq]
    res = []
    for i in range(0, len(floats), min_num):
        if i > 0 and op in {'m', 'M'}:
            op = 'l' if op == 'm' else 'L'
        res.extend([op, floats[i:i + min_num]])
    return res

def split_arc_values(op, value):
    float_re = r'(-?\d*\.?\d*(?:[eE][+-]?\d+)?)'
    flag_re = r'([1|0])'
    # 3 numb, 2 flags, 1 coord pair
    a_seq_re = r'[\s,]*'.join([
        float_re, float_re, float_re, flag_re, flag_re, float_re, float_re
    ]) + r'[\s,]*'
    res = []
    for seq in re.finditer(a_seq_re, value.strip()):
        res.extend([op, [float(num) for num in seq.groups()]])
    return res

def normalise_svg_path(attr):
    """Normalise SVG path.

    This basically introduces operator codes for multi-argument
    parameters. Also, it fixes sequences of consecutive M or m
    operators to MLLL... and mlll... operators. It adds an empty
    list as argument for Z and z only in order to make the resul-
    ting list easier to iterate over.

    E.g. "M 10 20, M 20 20, L 30 40, 40 40, Z"
      -> ['M', [10, 20], 'L', [20, 20], 'L', [30, 40], 'L', [40, 40], 'Z', []]
    """

    # operator codes mapped to the minimum number of expected arguments
    ops = {
        'A': 7, 'a': 7,
        'Q': 4, 'q': 4, 'T': 2, 't': 2, 'S': 4, 's': 4,
        'M': 2, 'L': 2, 'm': 2, 'l': 2, 'H': 1, 'V': 1,
        'h': 1, 'v': 1, 'C': 6, 'c': 6, 'Z': 0, 'z': 0,
    }
    op_keys = ops.keys()

    # do some preprocessing
    result = []
    groups = re.split('([achlmqstvz])', attr.strip(), flags=re.I)
    op = None
    for item in groups:
        if item.strip() == '':
            continue
        if item in op_keys:
            # fix sequences of M to one M plus a sequence of L operators,
            # same for m and l.
            if item == 'M' and item == op:
                op = 'L'
            elif item == 'm' and item == op:
                op = 'l'
            else:
                op = item
            if ops[op] == 0:  # Z, z
                result.extend([op, []])
        else:
            if op.lower() == 'a':
                result.extend(split_arc_values(op, item))
            else:
                result.extend(split_floats(op, ops[op], item))
            op = result[-2]  # Remember last op

    return result

def convert_quadratic_to_cubic_path(q0, q1, q2):
    """
    Convert a quadratic Bezier curve through q0, q1, q2 to a cubic one.
    """
    c0 = q0
    c1 = (q0[0] + 2 / 3 * (q1[0] - q0[0]), q0[1] + 2 / 3 * (q1[1] - q0[1]))
    c2 = (c1[0] + 1 / 3 * (q2[0] - q0[0]), c1[1] + 1 / 3 * (q2[1] - q0[1]))
    c3 = q2
    return c0, c1, c2, c3

# ***********************************************
# Helper functions for elliptical arc conversion.
# ***********************************************
def vector_angle(u, v):
    d = hypot(*u) * hypot(*v)
    if d == 0:
        return 0
    c = (u[0] * v[0] + u[1] * v[1]) / d
    if c < -1:
        c = -1
    elif c > 1:
        c = 1
    s = u[0] * v[1] - u[1] * v[0]
    return degrees(copysign(acos(c), s))

def end_point_to_center_parameters(x1, y1, x2, y2, fA, fS, rx, ry, phi=0):
    '''
    See http://www.w3.org/TR/SVG/implnote.html#ArcImplementationNotes F.6.5
    note that we reduce phi to zero outside this routine
    '''
    rx = fabs(rx)
    ry = fabs(ry)

    # step 1
    if phi:
        phi_rad = radians(phi)
        sin_phi = sin(phi_rad)
        cos_phi = cos(phi_rad)
        tx = 0.5 * (x1 - x2)
        ty = 0.5 * (y1 - y2)
        x1d = cos_phi * tx - sin_phi * ty
        y1d = sin_phi * tx + cos_phi * ty
    else:
        x1d = 0.5 * (x1 - x2)
        y1d = 0.5 * (y1 - y2)

    # step 2
    # we need to calculate
    # (rx*rx*ry*ry-rx*rx*y1d*y1d-ry*ry*x1d*x1d)
    # -----------------------------------------
    #     (rx*rx*y1d*y1d+ry*ry*x1d*x1d)
    #
    # that is equivalent to
    #
    #          rx*rx*ry*ry
    # = -----------------------------  -    1
    #   (rx*rx*y1d*y1d+ry*ry*x1d*x1d)
    #
    #              1
    # = -------------------------------- - 1
    #   x1d*x1d/(rx*rx) + y1d*y1d/(ry*ry)
    #
    # = 1/r - 1
    #
    # it turns out r is what they recommend checking
    # for the negative radicand case
    r = x1d * x1d / (rx * rx) + y1d * y1d / (ry * ry)
    if r > 1:
        rr = sqrt(r)
        rx *= rr
        ry *= rr
        r = x1d * x1d / (rx * rx) + y1d * y1d / (ry * ry)
        r = 1 / r - 1
    elif r != 0:
        r = 1 / r - 1
    if -1e-10 < r < 0:
        r = 0
    r = sqrt(r)
    if fA == fS:
        r = -r
    cxd = (r * rx * y1d) / ry
    cyd = -(r * ry * x1d) / rx

    # step 3
    if phi:
        cx = cos_phi * cxd - sin_phi * cyd + 0.5 * (x1 + x2)
        cy = sin_phi * cxd + cos_phi * cyd + 0.5 * (y1 + y2)
    else:
        cx = cxd + 0.5 * (x1 + x2)
        cy = cyd + 0.5 * (y1 + y2)

    # step 4
    theta1 = vector_angle((1, 0), ((x1d - cxd) / rx, (y1d - cyd) / ry))
    dtheta = vector_angle(
        ((x1d - cxd) / rx, (y1d - cyd) / ry),
        ((-x1d - cxd) / rx, (-y1d - cyd) / ry)
    ) % 360
    if fS == 0 and dtheta > 0:
        dtheta -= 360
    elif fS == 1 and dtheta < 0:
        dtheta += 360
    return cx, cy, rx, ry, -theta1, -dtheta

def bezier_arc_from_centre(cx, cy, rx, ry, start_ang=0, extent=90):
    if abs(extent) <= 90:
        nfrag = 1
        frag_angle = extent
    else:
        nfrag = ceil(abs(extent) / 90)
        frag_angle = extent / nfrag
    if frag_angle == 0:
        return []

    frag_rad = radians(frag_angle)
    half_rad = frag_rad * 0.5
    kappa = abs(4 / 3 * (1 - cos(half_rad)) / sin(half_rad))

    if frag_angle < 0:
        kappa = -kappa

    point_list = []
    theta1 = radians(start_ang)
    start_rad = theta1 + frag_rad

    c1 = cos(theta1)
    s1 = sin(theta1)
    for i in range(nfrag):
        c0 = c1
        s0 = s1
        theta1 = start_rad + i * frag_rad
        c1 = cos(theta1)
        s1 = sin(theta1)
        point_list.append((cx + rx * c0,
                          cy - ry * s0,
                          cx + rx * (c0 - kappa * s0),
                          cy - ry * (s0 + kappa * c0),
                          cx + rx * (c1 + kappa * s1),
                          cy - ry * (s1 - kappa * c1),
                          cx + rx * c1,
                          cy - ry * s1))
    return point_list

def bezier_arc_from_end_points(x1, y1, rx, ry, phi, fA, fS, x2, y2):
    if (x1 == x2 and y1 == y2):
        # From https://www.w3.org/TR/SVG/implnote.html#ArcImplementationNotes:
        # If the endpoints (x1, y1) and (x2, y2) are identical, then this is
        # equivalent to omitting the elliptical arc segment entirely.
        return []
    if phi:
        # Our box bezier arcs can't handle rotations directly
        # move to a well known point, eliminate phi and transform the other point
        mx = mmult(rotate(-phi), translate(-x1, -y1))
        tx2, ty2 = transformPoint(mx, (x2, y2))
        # Convert to box form in unrotated coords
        cx, cy, rx, ry, start_ang, extent = end_point_to_center_parameters(
            0, 0, tx2, ty2, fA, fS, rx, ry
        )
        bp = bezier_arc_from_centre(cx, cy, rx, ry, start_ang, extent)
        # Re-rotate by the desired angle and add back the translation
        mx = mmult(translate(x1, y1), rotate(phi))
        res = []
        for x1, y1, x2, y2, x3, y3, x4, y4 in bp:
            res.append(
                transformPoint(mx, (x1, y1)) + transformPoint(mx, (x2, y2)) +
                transformPoint(mx, (x3, y3)) + transformPoint(mx, (x4, y4))
            )
        return res
    else:
        cx, cy, rx, ry, start_ang, extent = end_point_to_center_parameters(
            x1, y1, x2, y2, fA, fS, rx, ry
        )
        return bezier_arc_from_centre(cx, cy, rx, ry, start_ang, extent)

class SvgPath(Path,UserNode):
    """Path, from an svg path string"""
    def __init__(self, s, isClipPath=0, autoclose=None, fillMode=FILL_EVEN_ODD, **kw):
        vswap = kw.pop('vswap',0)
        hswap = kw.pop('hswap',0)
        super().__init__(
                        points=None,operators=None,
                        isClipPath=isClipPath,
                        autoclose=autoclose,
                        fillMode=fillMode, **kw)
        if not s: return
        normPath = normalise_svg_path(s)
        points = self.points
        # Track subpaths needing to be closed later
        unclosed_subpath_pointers = []
        subpath_start = []
        lastop = ''
        last_quadratic_cp = None

        for i in range(0, len(normPath), 2):
            op, nums = normPath[i:i+2]

            if op in ('m', 'M') and i > 0 and self.operators[-1] != _CLOSEPATH:
                unclosed_subpath_pointers.append(len(self.operators))

            # moveto absolute
            if op == 'M':
                self.moveTo(*nums)
                subpath_start = points[-2:]
            # lineto absolute
            elif op == 'L':
                self.lineTo(*nums)

            # moveto relative
            elif op == 'm':
                if len(points) >= 2:
                    if lastop in ('Z', 'z'):
                        starting_point = subpath_start
                    else:
                        starting_point = points[-2:]
                    xn, yn = starting_point[0] + nums[0], starting_point[1] + nums[1]
                    self.moveTo(xn, yn)
                else:
                    self.moveTo(*nums)
                subpath_start = points[-2:]
            # lineto relative
            elif op == 'l':
                xn, yn = points[-2] + nums[0], points[-1] + nums[1]
                self.lineTo(xn, yn)

            # horizontal/vertical line absolute
            elif op == 'H':
                self.lineTo(nums[0], points[-1])
            elif op == 'V':
                self.lineTo(points[-2], nums[0])

            # horizontal/vertical line relative
            elif op == 'h':
                self.lineTo(points[-2] + nums[0], points[-1])
            elif op == 'v':
                self.lineTo(points[-2], points[-1] + nums[0])

            # cubic bezier, absolute
            elif op == 'C':
                self.curveTo(*nums)
            elif op == 'S':
                x2, y2, xn, yn = nums
                if len(points) < 4 or lastop not in {'c', 'C', 's', 'S'}:
                    xp, yp, x0, y0 = points[-2:] * 2
                else:
                    xp, yp, x0, y0 = points[-4:]
                xi, yi = x0 + (x0 - xp), y0 + (y0 - yp)
                self.curveTo(xi, yi, x2, y2, xn, yn)

            # cubic bezier, relative
            elif op == 'c':
                xp, yp = points[-2:]
                x1, y1, x2, y2, xn, yn = nums
                self.curveTo(xp + x1, yp + y1, xp + x2, yp + y2, xp + xn, yp + yn)
            elif op == 's':
                x2, y2, xn, yn = nums
                if len(points) < 4 or lastop not in {'c', 'C', 's', 'S'}:
                    xp, yp, x0, y0 = points[-2:] * 2
                else:
                    xp, yp, x0, y0 = points[-4:]
                xi, yi = x0 + (x0 - xp), y0 + (y0 - yp)
                self.curveTo(xi, yi, x0 + x2, y0 + y2, x0 + xn, y0 + yn)

            # quadratic bezier, absolute
            elif op == 'Q':
                x0, y0 = points[-2:]
                x1, y1, xn, yn = nums
                last_quadratic_cp = (x1, y1)
                (x0, y0), (x1, y1), (x2, y2), (xn, yn) = \
                    convert_quadratic_to_cubic_path((x0, y0), (x1, y1), (xn, yn))
                self.curveTo(x1, y1, x2, y2, xn, yn)
            elif op == 'T':
                if last_quadratic_cp is not None:
                    xp, yp = last_quadratic_cp
                else:
                    xp, yp = points[-2:]
                x0, y0 = points[-2:]
                xi, yi = x0 + (x0 - xp), y0 + (y0 - yp)
                last_quadratic_cp = (xi, yi)
                xn, yn = nums
                (x0, y0), (x1, y1), (x2, y2), (xn, yn) = \
                    convert_quadratic_to_cubic_path((x0, y0), (xi, yi), (xn, yn))
                self.curveTo(x1, y1, x2, y2, xn, yn)

            # quadratic bezier, relative
            elif op == 'q':
                x0, y0 = points[-2:]
                x1, y1, xn, yn = nums
                x1, y1, xn, yn = x0 + x1, y0 + y1, x0 + xn, y0 + yn
                last_quadratic_cp = (x1, y1)
                (x0, y0), (x1, y1), (x2, y2), (xn, yn) = \
                    convert_quadratic_to_cubic_path((x0, y0), (x1, y1), (xn, yn))
                self.curveTo(x1, y1, x2, y2, xn, yn)
            elif op == 't':
                if last_quadratic_cp is not None:
                    xp, yp = last_quadratic_cp
                else:
                    xp, yp = points[-2:]
                x0, y0 = points[-2:]
                xn, yn = nums
                xn, yn = x0 + xn, y0 + yn
                xi, yi = x0 + (x0 - xp), y0 + (y0 - yp)
                last_quadratic_cp = (xi, yi)
                (x0, y0), (x1, y1), (x2, y2), (xn, yn) = \
                    convert_quadratic_to_cubic_path((x0, y0), (xi, yi), (xn, yn))
                self.curveTo(x1, y1, x2, y2, xn, yn)

            # elliptical arc
            elif op in ('A', 'a'):
                rx, ry, phi, fA, fS, x2, y2 = nums
                x1, y1 = points[-2:]
                if op == 'a':
                    x2 += x1
                    y2 += y1
                if abs(rx) <= 1e-10 or abs(ry) <= 1e-10:
                    self.lineTo(x2, y2)
                else:
                    bp = bezier_arc_from_end_points(x1, y1, rx, ry, phi, fA, fS, x2, y2)
                    for _, _, x1, y1, x2, y2, xn, yn in bp:
                        self.curveTo(x1, y1, x2, y2, xn, yn)

            # close self
            elif op in ('Z', 'z'):
                self.closePath()

            else:
                logger.debug("Suspicious self operator: %s", op)

            if op not in ('Q', 'q', 'T', 't'):
                last_quadratic_cp = None
            lastop = op

        if self.operators[-1] != _CLOSEPATH:
            unclosed_subpath_pointers.append(len(self.operators))

        if vswap or hswap:
            b = self.getBounds()
            if hswap:
                m = b[2]+b[0]
                for i in range(0,len(points),2):
                    points[i] = m - points[i]
            if vswap:
                m = b[3]+b[1]
                for i in range(1,len(points),2):
                    points[i] = m - points[i]

        if unclosed_subpath_pointers and self.fillColor is not None:
            # ReportLab doesn't fill unclosed paths, so we are creating a copy
            # of self with all subpaths closed, but without stroke.
            # https://bitbucket.org/rptlab/reportlab/issues/99/
            closed_path = Path()
            closed_path.__dict__.update(copy.deepcopy(self.__dict__))
            for pointer in reversed(unclosed_subpath_pointers):
                closed_path.operators.insert(pointer, _CLOSEPATH)
            self.__closed_path = closed_path
            self.fillColor = None
        else:
            self.__closed_path = None

    def provideNode(self):
        p = Path()
        p.__dict__ = self.__dict__.copy()
        del p._SvgPath__closed_path
        if self.__closed_path:
            g = Group()
            g.add(self.__closed_path)
            g.add(p)
            return g
        else:
            return p
