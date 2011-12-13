/*
    OpenERP, Open Source Business Applications
    Copyright (c) 2011 OpenERP S.A. <http://openerp.com>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/


﻿using System.Collections;

namespace OpenERPClient
{
    public class Record
    {
        public long id;
        public string name;
        public Model model;
        public Hashtable columns;
        public Record(long id, string name, Model model)
        {
            /*
            It gives the record of id, name and model.
            :param id : record id.
            :param name : record name.
            :param model : model name.
            */

            this.id = id;
            this.name = name;
            this.model = model;
        }
        public Record(Hashtable columns, Model model)
        {
            /*
            It gives the records in hashtable columns and also model name.
            :param columns : hashtable column values.
            :param model : model name.
            */

            this.id = long.Parse(columns["id"].ToString());
            if (columns.ContainsKey("name"))
            {
                this.name = columns["name"].ToString();
            }
            this.model = model;
            this.columns = columns;
        }
        public override string ToString()
        {
            /*
            It will override the Tostring.
            */

            if (this.name != null) return this.name;
            return this.id.ToString();
        }
    }
}
