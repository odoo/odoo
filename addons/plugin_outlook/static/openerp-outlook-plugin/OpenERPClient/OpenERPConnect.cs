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


using System;
using System.Windows.Forms;
using System.Collections;
using CookComputing.XmlRpc;

namespace OpenERPClient
{
    public class ServiceUrl : System.Attribute
    {
        string _url;
        public ServiceUrl(string url)
        {
            /*
            It will contain the ServiceUrl.
            :param url : url with server and port.
            */

            this._url = url;
        }
        public string Url
        {
            /*
            It will get and return the Url for the connection.
             
            :return : String 
            */

            get
            {
                return _url;
            }
        }
        public override string ToString()
        {
            /*
            It will override the Tostring and return the _url.
            */

            return this._url;
        }
    }
    public enum OpenERPService
    {
        [ServiceUrl("/xmlrpc/object")]
        Object = 1,
        [ServiceUrl("/xmlrpc/db")]
        DB = 2,
        [ServiceUrl("/xmlrpc/common")]
        Common = 3
    }
    public class OpenERPConnect
    {
        int uid;
        string url;
        string dbname;
        string login;
        string pwd;
        bool chkpwd;
        string password;
        public string URL
        {
            /*
            It will get and set the value of the url.
            
            :return : String
            */

            get
            {
                return url;
            }
            set
            {
                url = value;
            }
        }
        public string DBName
        {
            /*
            It will get and set the value of the Database Name.
            
            :return : String
            */

            get
            {
                return dbname;
            }
            set
            {
                dbname = value;
            }
        }
        public string UserId
        {
            /*
            It will get and set the value of the UserId.
            
            :return : String
            */

            get
            {
                return login;
            }
            set
            {
                login = value;
            }
        }
        public string pswrd
        {
            /*
            It will get and set the value of the Password.
            
            :return : String
            */

            get
            {
                return password;
            }
            set
            {
                password = value;
            }
        }

        public bool rempwd
        {
            /*
            It will get and set the value of the Remember Password.
            
            :return : True or False
            */

            get
            {
                return chkpwd;
            }
            set
            {
                chkpwd = value;
            }
        }

        public string version;
        XMLRPCClient rpcclient;

        public void Open(Enum service)
        {
            /*
            It opens the connetion by the url and service url.
            :param service : enum service.
            */

            string url = null;
            Type type = service.GetType();

            ServiceUrl[] _urls =
               type.GetField(service.ToString()).GetCustomAttributes(typeof(ServiceUrl),
                                       false) as ServiceUrl[];
            if (_urls.Length > 0)
            {
                url = _urls[0].Url;
            }

            this.Open(url);


        }

        void Open(string service_url)
        {
            /*
            It opens rpcclient by service url.
            :param service_url : service url
            */

            this.rpcclient = new XMLRPCClient(this.url + service_url);

        }
        void Close()
        {
            /*
            It closes rpcclient.
            */

            this.rpcclient = null;

        }
        public OpenERPConnect()
        {
        }
        public OpenERPConnect(string url)
        {
            /*
             It will contain the url wit the server and port.
             :param url : url with the server and port.
            */

            this.url = url;
        }
        public OpenERPConnect(string url, string dbname, string login, string pwd)
        {
            /*
             It will do the connection with OpenERP server.
             :param url : url with the server and port.
             :param dbname : the list of database.
             :param login : user name.
             :param pwd : password.
            */

            this.url = url;
            this.dbname = dbname;
            this.login = login;
            this.pwd = pwd;
            this.version = ServerVersion();
        }
        public Boolean isLoggedIn
        {
            /*
            It will check whether successfully login to OpenERP is done or not.
            
            :return : True or False.
            */

            get
            {
                if (this.uid > 0) { return true; }
                return false;
            }
        }

        public int Login(string dbname, string userid, string pwd)
        {
            /*
             It will check whether the entered dbname, userid and password are correct or not
             and on that basis it will allow the user for connecting to OpenERP.
             :param dbname : list of database
             :param userid : userid 
             :param pwd : password of the user
             
             :return : Integer
            */

            this.Open(OpenERPClient.OpenERPService.Common);
            object isLogin = this.rpcclient.Login(dbname, userid, pwd);
            this.uid = 0;
            if (Convert.ToBoolean(isLogin))
            {
                this.uid = Convert.ToInt32(isLogin);
            }
            this.pwd = pwd;
            if (this.uid <= 0)
            {
                MessageBox.Show("Authentication Error!\nBad username and password.", Form.ActiveForm.Text, MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
            this.Close();
            return this.uid;

        }
        XmlRpcStruct ConvertAs(Hashtable value)
        {
            /*
             It will convert the Hashtable into XmlRpcStruct and vise-versa.
             
             :param value : Hasheable value.
              
             :retutn : Hashtable values and vise versa the XmlRpcStruct value.
            */

            XmlRpcStruct new_value;
            new_value = new XmlRpcStruct();
            foreach (string key in value.Keys)
            {
                object res;
                if (value[key] == null)
                {
                    res = "";
                }
                if (value[key].GetType() == typeof(Hashtable))
                {
                    res = this.ConvertAs((Hashtable)value[key]);
                }
                else
                {
                    res = value[key];
                }
                new_value.Add(key, res);
            }
            return new_value;
        }
        object[] ConvertArgs(object[] args)
        {
            /*
            It will convert the arguments which are of type Hashtable into new arguments.
            
            :param args : Objet value of arguments
              
            :return : Object value of arguments.
            */

            for (int i = 0; i < args.Length; i++)
            {
                object arg = args[i];
                XmlRpcStruct new_arg;
                if (arg.GetType() == typeof(Hashtable))
                {
                    new_arg = this.ConvertAs((Hashtable)arg);
                    args[i] = new_arg;
                }
            }
            return args;
        }
        public object Execute(string model, string method, params object[] args)
        {
            /*
            It executes the model name, the method name and also the list of arrays arguments.
            :param model : model name.
            :param method : method name.
            :params args : list of arrays of arguments.
            
            :return : Object
            */

            args = this.ConvertArgs(args);
            this.Open(OpenERPClient.OpenERPService.Object);

            object res = this.rpcclient.Execute(this.dbname, this.uid, this.pwd, model, method, args);
            this.Close();
            return res;
        }
        public object[] DBList()
        {
            /*
            It will return the list of the database which will be created.
             
            :return : Database List 
            */

            this.Open(OpenERPClient.OpenERPService.DB);
            object[] res = this.rpcclient.DBList();
            this.Close();
            return res;
        }
        public string ServerVersion()
        {
            /*
            It will give the version of the server which the user is using.
              
            :return : String
            */

            this.Open(OpenERPClient.OpenERPService.DB);
            string version = this.rpcclient.ServerVersion();
            this.Close();
            return version;
        }


    }

}
