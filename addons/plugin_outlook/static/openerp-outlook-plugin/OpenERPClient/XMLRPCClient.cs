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
using System.Text;
using CookComputing.XmlRpc;

namespace OpenERPClient
{
    public interface IOpenERPCommon : IXmlRpcProxy
    {
        [XmlRpcMethod("login")]
        object Login(string dbname, string username, string pwd);

    }
    public interface IOpenERPObject : IXmlRpcProxy
    {

        [XmlRpcMethod("execute")]
        Object Execute(string dbName, long userId, string pwd, string model, string method, params Object[] args);



    }
    public interface IOpenERPDB : IXmlRpcProxy
    {

        [XmlRpcMethod("list")]
        Object[] DBList();

        [XmlRpcMethod("server_version")]
        string ServerVersion();

    }
    public interface Ixmlrpcconnect : IOpenERPCommon, IOpenERPDB, IOpenERPObject
    {
    }
    public class XMLRPCClient : Ixmlrpcconnect
    {
        Ixmlrpcconnect rpcclient = (Ixmlrpcconnect)XmlRpcProxyGen.Create(typeof(Ixmlrpcconnect));
        public XMLRPCClient(string ServiceUrl)
        {
            rpcclient.Url = ServiceUrl;
        }

        #region Ixmlrpcconnect Members

        public object Login(string dbname, string username, string pwd)
        {
            return rpcclient.Login(dbname, username, pwd);
        }

        public object Execute(string dbName, long userId, string pwd, string model, string method, params object[] args)
        {
            return rpcclient.Execute(dbName, userId, pwd, model, method, args);
        }

        public object[] DBList()
        {
            return rpcclient.DBList();
        }

        public string ServerVersion()
        {
            return rpcclient.ServerVersion();
        }
        #endregion


        #region IXmlRpcProxy Members

        public bool AllowAutoRedirect
        {
            get
            {
                throw new NotImplementedException();
            }
            set
            {
                throw new NotImplementedException();
            }
        }

        public System.Security.Cryptography.X509Certificates.X509CertificateCollection ClientCertificates
        {
            get { throw new NotImplementedException(); }
        }

        public string ConnectionGroupName
        {
            get
            {
                throw new NotImplementedException();
            }
            set
            {
                throw new NotImplementedException();
            }
        }

        public System.Net.CookieContainer CookieContainer
        {
            get { throw new NotImplementedException(); }
        }

        public System.Net.ICredentials Credentials
        {
            get
            {
                throw new NotImplementedException();
            }
            set
            {
                throw new NotImplementedException();
            }
        }

        public bool EnableCompression
        {
            get
            {
                throw new NotImplementedException();
            }
            set
            {
                throw new NotImplementedException();
            }
        }

        public bool Expect100Continue
        {
            get
            {
                throw new NotImplementedException();
            }
            set
            {
                throw new NotImplementedException();
            }
        }

        public System.Net.WebHeaderCollection Headers
        {
            get { throw new NotImplementedException(); }
        }

        public Guid Id
        {
            get { throw new NotImplementedException(); }
        }

        public int Indentation
        {
            get
            {
                throw new NotImplementedException();
            }
            set
            {
                throw new NotImplementedException();
            }
        }

        public bool KeepAlive
        {
            get
            {
                throw new NotImplementedException();
            }
            set
            {
                throw new NotImplementedException();
            }
        }

        public XmlRpcNonStandard NonStandard
        {
            get
            {
                throw new NotImplementedException();
            }
            set
            {
                throw new NotImplementedException();
            }
        }

        public bool PreAuthenticate
        {
            get
            {
                throw new NotImplementedException();
            }
            set
            {
                throw new NotImplementedException();
            }
        }

        public Version ProtocolVersion
        {
            get
            {
                throw new NotImplementedException();
            }
            set
            {
                throw new NotImplementedException();
            }
        }

        public System.Net.IWebProxy Proxy
        {
            get
            {
                throw new NotImplementedException();
            }
            set
            {
                throw new NotImplementedException();
            }
        }

        public System.Net.CookieCollection ResponseCookies
        {
            get { throw new NotImplementedException(); }
        }

        public System.Net.WebHeaderCollection ResponseHeaders
        {
            get { throw new NotImplementedException(); }
        }

        public int Timeout
        {
            get
            {
                throw new NotImplementedException();
            }
            set
            {
                throw new NotImplementedException();
            }
        }

        public string Url
        {
            get
            {
                throw new NotImplementedException();
            }
            set
            {
                throw new NotImplementedException();
            }
        }

        public bool UseEmptyParamsTag
        {
            get
            {
                throw new NotImplementedException();
            }
            set
            {
                throw new NotImplementedException();
            }
        }

        public bool UseIndentation
        {
            get
            {
                throw new NotImplementedException();
            }
            set
            {
                throw new NotImplementedException();
            }
        }

        public bool UseIntTag
        {
            get
            {
                throw new NotImplementedException();
            }
            set
            {
                throw new NotImplementedException();
            }
        }

        public bool UseStringTag
        {
            get
            {
                throw new NotImplementedException();
            }
            set
            {
                throw new NotImplementedException();
            }
        }

        public string UserAgent
        {
            get
            {
                throw new NotImplementedException();
            }
            set
            {
                throw new NotImplementedException();
            }
        }

        public Encoding XmlEncoding
        {
            get
            {
                throw new NotImplementedException();
            }
            set
            {
                throw new NotImplementedException();
            }
        }

        public string XmlRpcMethod
        {
            get
            {
                throw new NotImplementedException();
            }
            set
            {
                throw new NotImplementedException();
            }
        }

        public string[] SystemListMethods()
        {
            throw new NotImplementedException();
        }

        public object[] SystemMethodSignature(string MethodName)
        {
            throw new NotImplementedException();
        }

        public string SystemMethodHelp(string MethodName)
        {
            throw new NotImplementedException();
        }

        public event XmlRpcRequestEventHandler RequestEvent;

        public event XmlRpcResponseEventHandler ResponseEvent;

        #endregion
    }
}
