##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
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

import time

def som(cr, uid, partner_id, args):
	result = args['som_interval_default']
	max = args['som_interval_max'] or 4
	factor = args['som_interval_decrease']
	date_start=time.time() - args['som_interval']*3600*24*max
	for i in range(max):
		next_date = date_start + args['som_interval']*3600*24
		cr.execute(
			 '''
			 select s.factor from res_partner_event e
			 left join res_partner_som s
			 on (e.som=s.id) where partner_id=%d and date>=%s and date<%s''', 
			 (partner_id, 
			  time.strftime('%Y-%m-%d', time.gmtime(date_start)),
			  time.strftime('%Y-%m-%d', time.gmtime(next_date))))

		soms = cr.fetchall()
		if len(soms):
			c = 0
			nbr = 0.0
			for som in soms:
				if som[0]:
					c+=1
					nbr+=som[0]
			if c:
				avg = nbr/c
			else:
				avg = result
			result = result*(1-factor) + (avg*factor)
		else:
			avg = args['som_interval_default']
		date_start = next_date
	return result


