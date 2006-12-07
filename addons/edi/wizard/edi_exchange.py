##############################################################################
#
# Copyright (c) 2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

def stripnulls(data):
	return data.replace("\00", "").strip()

def fillleft(data, length):
	while len(str(data))<length:
		data=" "+str(data)
	return data

def fillright(data, length):
	while len(str(data))<length:
		data=str(data)+" "
	return data

def fillzero(data, length):
	while len(str(data))<length:
		data="0"+str(data)
	return data

class edi_exchange:

	hint_struct = { "sender":		(   4,  39, stripnulls, fillright),
					"receiver":		(  57,  92, stripnulls, fillright),
					"date":			( 110, 118, stripnulls, fillright),
					"time":			( 118, 122, stripnulls, fillleft),
				}
	
	hgen_struct = { "message-type":	(  32,  43, stripnulls, fillright),
					"order-num":	(  43,  78, stripnulls, fillright),
					"order-date":	(  78,  86, stripnulls, fillright),
					"currency":		( 101, 104, stripnulls, fillright),
				}
	
	hpty_struct = { "partner-type":	(   4,   7, stripnulls, fillright),
					"partner-code":	(   7,  24, stripnulls, fillright),
				}
	
	hdel_struct = { "deliv-date":	(   4,  12, stripnulls, fillright),
					"deliv-time":	(  12,  16, stripnulls, fillright),
					"deliv-q":		(  16,  19, stripnulls, fillright),
				}
	
	hftx_struct = { "text-q":		(   4,   7, stripnulls, fillright),
					"text":			(   7, 209, stripnulls, fillright),
				}
	
	dftx_struct = { "text-q":		(   4,   7, stripnulls, fillright),
					"text":			(   7, 209, stripnulls, fillright),
				}
	
	dart_struct = { "line-num":		(   4,  10, stripnulls, fillzero),
					"barcode":		(  13,  48, stripnulls, fillright),
					"quantity21":	(  89, 104, stripnulls, fillzero),
					"unit21":		( 107, 110, stripnulls, fillright),
					"quantity59":	( 110, 125, stripnulls, fillzero),
					"unit59":		( 128, 131, stripnulls, fillright),
					"price":		( 131, 146, stripnulls, fillzero),
					"price-q":		( 146, 149, stripnulls, fillright),
					"price-unit":	( 149, 152, stripnulls, fillright),
					"hint-price":	( 152, 167, stripnulls, fillright),
					"hint-price-q": ( 167, 170, stripnulls, fillright),
					"hint-price-u": ( 170, 173, stripnulls, fillright),
					"ref86":		( 173, 181, stripnulls, fillright),
					"shop-code":	( 181, 196, stripnulls, fillright),
					"item-key":		( 196, 209, stripnulls, fillright),
					"shop-key":		( 209, 215, stripnulls, fillright),
					"log-unit-num":	( 215, 220, stripnulls, fillright),
				}
	
	dpty_struct = { "shop-barcode":	(   7,  24, stripnulls, fillright),
				}

	ddel_struct = { "deliv-date":	(   4,  12, stripnulls, fillright),
					"deliv-time":	(  12,  16, stripnulls, fillright),
				}

	dpid_struct = { "ident-art":	(   7,  42, stripnulls, fillright),
				}

	def parse_line(cls, line):
		lineDict = {}
		if hasattr(cls,line[:4].lower()+"_struct"):
			for field, tuple in getattr(cls,line[:4].lower()+"_struct").items():
				start, end, parseFunc, writeFunc = tuple
				lineDict[field] = parseFunc(line[start:end])
			return line[:4], lineDict
		else:
			return line[:4], {}
		
	parse_line = classmethod(parse_line)

	def create_line(cls, line):
		lineDict = {}
		outline=line['type'].upper()+" "*250+"\r\n"
		if hasattr(cls,line['type'].lower()+"_struct"):
			for field, tuple in getattr(cls, line['type'].lower()+"_struct").items():
				start, end, parseFunc, writeFunc = tuple
				outline=outline[0:start]+writeFunc(line[field], end-start)+outline[end:]
		return outline
	
	create_line = classmethod(create_line)
