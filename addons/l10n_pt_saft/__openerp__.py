# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2013 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Autores:
#	  Este software baseia-se no trabalho inicial de Paulino Ascenção <paulino1@sapo.pt> (l10n_pt_saft-6)
#    Adaptado à versão 7 por João Figueira<jjnf@communities.pt> e Jorge A. Ferreira <sysop.x0@gmail.com>
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
#
{
	'name' : 'Portugal : implementação do saft',
	'version' : '0.1',

	# SysOp
	#	'depends' : ['account'],
	'depends': ['base', 'account'],	
	'author' : 'Paulino Ascenção, João Figueira, Jorge A. Ferreira',
	'category' : 'Localisation/Account charts',

	'description': """
Implementação da versão portuguesa do Ficheiro para auditoria fiscal.
================================================================================
SAFT - Standard Audit File for Tax purposes
Módulo l10n_pt_saft.

""",



	'website': 'www.communities.pt',
	'data' : ['saft_view.xml'], 
	'demo' : [],
	'auto_install': False,
	'installable': True,
}
