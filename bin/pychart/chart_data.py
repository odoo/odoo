# -*- coding: utf-8 -*-
#
# Copyright (C) 2000-2005 by Yasushi Saito (yasushi.saito@gmail.com)
# 
# Jockey is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2, or (at your option) any
# later version.
#
# Jockey is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
import pychart_util
import copy
import math

def _convert_item(v, typ, line):
    if typ == "a":
        try:
            i = float(v)
        except ValueError: # non-number
            i = v
        return i
    elif typ == "d":
        try:
            return int(v)
        except ValueError:
            raise ValueError, "Can't convert %s to int; line=%s" % (v, line)
    elif typ == "f":
        try:
            return float(v)
        except ValueError:
            raise ValueError, "Can't convert %s to float; line=%s" % (v, line)
    elif typ == "s":
        return v
    else:
        raise ValueError, "Unknown conversion type, type=%s; line=%s" % (typ,line)
        
def parse_line(line, delim):
    if delim.find("%") < 0:
        return [ _convert_item(item, "a", None) for item in line.split(delim) ]
    
    data = []
    idx = 0 # indexes delim
    ch = 'f'
    sep = ','

    while idx < len(delim):
        if delim[idx] != '%':
            raise ValueError, "bad delimitor: '" + delim + "'"
        ch = delim[idx+1]
        idx += 2
        sep = ""
        while idx < len(delim) and delim[idx] != '%':
            sep += delim[idx]
            idx += 1
        xx = line.split(sep, 1)
        data.append(_convert_item(xx[0], ch, line))
        if len(xx) >= 2:
            line = xx[1]
        else:
            line = ""
            break

    if line != "":
        for item in line.split(sep):
            data.append(_convert_item(item, ch, line))
    return data

def escape_string(str):
    return str.replace("/", "//")

def extract_rows(data, *rows):
    """Extract rows specified in the argument list.

>>> chart_data.extract_rows([[10,20], [30,40], [50,60]], 1, 2)
[[30,40],[50,60]]
"""
    try:
        # for python 2.2
        # return [data[r] for r in rows]
        out = []
        for r in rows:
            out.append(data[r])
        return out
    except IndexError:
        raise IndexError, "data=%s rows=%s" % (data, rows)
    return out

def extract_columns(data, *cols):
    """Extract columns specified in the argument list.

>>> chart_data.extract_columns([[10,20], [30,40], [50,60]], 0)
[[10],[30],[50]]
"""
    out = []
    try:
        # for python 2.2:
        # return [ [r[c] for c in cols] for r in data]
        for r in data:
            col = []
            for c in cols:
                col.append(r[c])
            out.append(col)
    except IndexError:
        raise IndexError, "data=%s col=%s" % (data, col)        
    return out

            
            

def moving_average(data, xcol, ycol, width):
    """Compute the moving average of  YCOL'th column of each sample point
in  DATA. In particular, for each element  I in  DATA,
this function extracts up to  WIDTH*2+1 elements, consisting of
 I itself,  WIDTH elements before  I, and  WIDTH
elements after  I. It then computes the mean of the  YCOL'th
column of these elements, and it composes a two-element sample
consisting of  XCOL'th element and the mean.

>>> data = [[10,20], [20,30], [30,50], [40,70], [50,5]]
... chart_data.moving_average(data, 0, 1, 1)
[(10, 25.0), (20, 33.333333333333336), (30, 50.0), (40, 41.666666666666664), (50, 37.5)]

  The above value actually represents:

[(10, (20+30)/2), (20, (20+30+50)/3), (30, (30+50+70)/3), 
  (40, (50+70+5)/3), (50, (70+5)/2)]

"""

    
    out = []
    try:
        for i in range(len(data)):
            n = 0
            total = 0
            for j in range(i-width, i+width+1):
                if j >= 0 and j < len(data):
                    total += data[j][ycol]
                    n += 1
            out.append((data[i][xcol], float(total) / n))
    except IndexError:
        raise IndexError, "bad data: %s,xcol=%d,ycol=%d,width=%d" % (data,xcol,ycol,width)
    
    return out
    
def filter(func, data):
    """Parameter <func> must be a single-argument
    function that takes a sequence (i.e.,
a sample point) and returns a boolean. This procedure calls <func> on
each element in <data> and returns a list comprising elements for
which <func> returns True.

>>> data = [[1,5], [2,10], [3,13], [4,16]]
... chart_data.filter(lambda x: x[1] % 2 == 0, data)
[[2,10], [4,16]].
"""
    
    out = []
    for r in data:
	if func(r):
	    out.append(r)
    return out

def transform(func, data):
    """Apply <func> on each element in <data> and return the list
consisting of the return values from <func>.

>>> data = [[10,20], [30,40], [50,60]]
... chart_data.transform(lambda x: [x[0], x[1]+1], data)
[[10, 21], [30, 41], [50, 61]]

"""
    out = []
    for r in data:
        out.append(func(r))
    return out

def aggregate_rows(data, col):
    out = copy.deepcopy(data)
    total = 0
    for r in out:
        total += r[col]
        r[col] = total
    return out

def empty_line_p(s):
    return s.strip() == ""

def fread_csv(fd, delim = ','):
    """This function is similar to read_csv, except that it reads from
    an open file handle <fd>, or any object that provides method "readline".

fd = open("foo", "r")
data = chart_data.fread_csv(fd, ",") """
    
    data = []
    line = fd.readline()
    while line != "":
        if line[0] != '#' and not empty_line_p(line):
            data.append(parse_line(line, delim))
        line = fd.readline()
    return data

def read_csv(path, delim = ','):
    """This function reads
    comma-separated values from file <path>. Empty lines and lines
    beginning with "#" are ignored.  Parameter <delim> specifies how
    a line is separated into values. If it does not contain the
    letter "%", then <delim> marks the end of a value.
    Otherwise, this function acts like scanf in C:

chart_data.read_csv("file", "%d,%s:%d")

    Paramter <delim> currently supports
    only three conversion format specifiers:
    "d"(int), "f"(double), and "s"(string)."""
        
    f = open(path)
    data = fread_csv(f, delim)
    f.close()
    return data

def fwrite_csv(fd, data):
    """This function writes comma-separated <data> to <fd>. Parameter <fd> must be a file-like object
    that supports the |write()| method."""
    for v in data:
        fd.write(",".join([str(x) for x in v]))
        fd.write("\n")
        
def write_csv(path, data):
    """This function writes comma-separated values to <path>."""
    fd = file(path, "w")
    fwrite_csv(fd, data)
    fd.close()
    
def read_str(delim = ',', *lines):
    """This function is similar to read_csv, but it reads data from the
    list of <lines>.

fd = open("foo", "r")
data = chart_data.read_str(",", fd.readlines())"""

    data = []
    for line in lines:
        com = parse_line(line, delim)
        data.append(com)
    return data
    
def func(f, xmin, xmax, step = None):
    """Create sample points from function <f>, which must be a
    single-parameter function that returns a number (e.g., math.sin).
    Parameters <xmin> and <xmax> specify the first and last X values, and
    <step> specifies the sampling interval.

>>> chart_data.func(math.sin, 0, math.pi * 4, math.pi / 2)
[(0, 0.0), (1.5707963267948966, 1.0), (3.1415926535897931, 1.2246063538223773e-16), (4.7123889803846897, -1.0), (6.2831853071795862, -2.4492127076447545e-16), (7.8539816339744828, 1.0), (9.4247779607693793, 3.6738190614671318e-16), (10.995574287564276, -1.0)]

"""
    
    data = []
    x = xmin
    if not step:
        step = (xmax - xmin) / 100.0
    while x < xmax:
        data.append((x, f(x)))
        x += step
    return data

def _nr_data(data, col):
    nr_data = 0
    for d in data:
        nr_data += d[col]
    return nr_data
    
def median(data, freq_col=1):
    """Compute the median of the <freq_col>'th column of the values is <data>.

>>> chart_data.median([(10,20), (20,4), (30,5)], 0)
20
>>> chart_data.median([(10,20), (20,4), (30,5)], 1)
5.
    """
    
    nr_data = _nr_data(data, freq_col)
    median_idx = nr_data / 2
    i = 0
    for d in data:
        i += d[freq_col]
        if i >= median_idx:
            return d
    raise Exception, "??? median ???"

def cut_extremes(data, cutoff_percentage, freq_col=1):
    nr_data = _nr_data(data, freq_col)
    min_idx = nr_data * cutoff_percentage / 100.0
    max_idx = nr_data * (100 - cutoff_percentage) / 100.0
    r = []
    
    i = 0
    for d in data:
        if i < min_idx:
            if i + d[freq_col] >= min_idx:
                x = copy.deepcopy(d)
                x[freq_col] = x[freq_col] - (min_idx - i)
                r.append(x)
            i += d[freq_col]
            continue
	elif i + d[freq_col] >= max_idx:
            if i < max_idx and i + d[freq_col] >= max_idx:
                x = copy.deepcopy(d)
                x[freq_col] = x[freq_col] - (max_idx - i)
                r.append(x)
            break
        i += d[freq_col]
        r.append(d)
    return r

def mean(data, val_col, freq_col):
    nr_data = 0
    sum = 0
    for d in data:
        sum += d[val_col] * d[freq_col]
        nr_data += d[freq_col]
    if nr_data == 0:
	raise IndexError, "data is empty"

    return sum / float(nr_data)

def mean_samples(data, xcol, ycollist):
    """Create a sample list that contains
    the mean of the original list.

>>> chart_data.mean_samples([ [1, 10, 15], [2, 5, 10], [3, 8, 33] ], 0, (1, 2))
[(1, 12.5), (2, 7.5), (3, 20.5)]
"""
    out = []
    numcol = len(ycollist)
    try:
        for elem in data:
            v = 0
            for col in ycollist:
                v += elem[col]
            out.append( (elem[xcol], float(v) / numcol) )
    except IndexError:
        raise IndexError, "bad data: %s,xcol=%d,ycollist=%s" % (data,xcol,ycollist)
    
    return out

def stddev_samples(data, xcol, ycollist, delta = 1.0):
    """Create a sample list that contains the mean and standard deviation of the original list. Each element in the returned list contains following values: [MEAN, STDDEV, MEAN - STDDEV*delta, MEAN + STDDEV*delta].

>>> chart_data.stddev_samples([ [1, 10, 15, 12, 15], [2, 5, 10, 5, 10], [3, 32, 33, 35, 36], [4,16,66, 67, 68] ], 0, range(1,5))
[(1, 13.0, 2.1213203435596424, 10.878679656440358, 15.121320343559642), (2, 7.5, 2.5, 5.0, 10.0), (3, 34.0, 1.5811388300841898, 32.418861169915807, 35.581138830084193), (4, 54.25, 22.094965489902897, 32.155034510097103, 76.344965489902904)]
"""
    out = []
    numcol = len(ycollist)
    try:
        for elem in data:
            total = 0
            for col in ycollist:
                total += elem[col]
            mean = float(total) / numcol
            variance = 0
            for col in ycollist:
                variance += (mean - elem[col]) ** 2
            stddev = math.sqrt(variance / numcol) * delta
            out.append( (elem[xcol], mean, stddev, mean-stddev, mean+stddev) )
            
            
            
    except IndexError:
        raise IndexError, "bad data: %s,xcol=%d,ycollist=%s" % (data,xcol,ycollist)
    return out

def nearest_match(data, col, val):
    min_delta = None
    match = None
    
    for d in data:
        if min_delta == None or abs(d[col] - val) < min_delta:
            min_delta = abs(d[col] - val)
            match = d
    pychart_util.warn("XXX ", match)
    return match
