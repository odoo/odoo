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


﻿using System;
using System.Collections;
using System.Linq;

namespace OpenERPClient
{
    public class Model
    {
        public string model;
        public string name;
        protected OpenERPConnect openerp_connect;
        public OpenERPConnect Connection
        {
            set
            {
                this.openerp_connect = value;
            }
            get
            {
                return this.openerp_connect;
            }
        }
        public Model()
        {
        }
        public Model(string model)
        {
            /*
            It gives the model name only.
            :param model : madel name
            */

            this.model = model;
        }
        public Model(string model, string name)
        {
            /*
            It gives the model names with their descriptions.
            :param model : model name
            :param name : description of model
            */

            this.name = name;
            this.model = model;
        }
        public override string ToString()
        {
            /*
            It overrides the name of model into ToString.
            
            :return : String
            */ 

            if (this.name != null) return this.name;
            return this.model;
        }
      
    }
}
