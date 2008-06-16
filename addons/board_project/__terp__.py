##############################################################################
#
# Copyright (c) 2004-2008 Tiny SPRL (http://tiny.be) All Rights Reserved.
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
###############################################################################
{
	"name":"Board for project users",
	"version":"1.0",
	"author":"Tiny",
	"category":"Board/Projects & Services",
	"depends":[
		"project",
		"report_timesheet",
		"board",
		"report_analytic_planning",
		"report_analytic_line",
		"report_task",
		"hr_timesheet_sheet"
	],
	"demo_xml":["board_project_demo.xml"],
	"update_xml":["board_project_view.xml", "board_project_manager_view.xml"],
	"description": """
This module implements a dashboard for project member that includes:
	* List of my open tasks
	* List of my next deadlines
	* List of public notes
	* Graph of my timesheet
	* Graph of my work analysis
	""",
	"active":False,
	"installable":True,
}
