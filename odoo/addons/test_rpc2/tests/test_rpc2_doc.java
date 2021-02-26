import java.net.URL;
import java.util.*;
import org.xml.sax.SAXException;
import static java.util.Arrays.asList;
import static java.util.Collections.*;

import org.apache.ws.commons.util.NamespaceContextImpl;
import org.apache.xmlrpc.common.*;
import org.apache.xmlrpc.client.*;
import org.apache.xmlrpc.parser.*;
import org.apache.xmlrpc.serializer.*;
import org.apache.xmlrpc.XmlRpcException;

// adds support for <nil/>: https://zugiart.com/2011/07/apache-xml-rpc-handle-null-nil/
class CustomXmlRpcTypeNil extends TypeFactoryImpl {
    CustomXmlRpcTypeNil(XmlRpcClient c) {
        super(c);
    }
    public TypeParser getParser(XmlRpcStreamConfig pConfig, NamespaceContextImpl pContext, String pURI, String pLocalName) {
        return NullSerializer.NIL_TAG.equals(pLocalName)
            ? new NullParser()
            : super.getParser(pConfig, pContext, pURI, pLocalName);
    }
    public TypeSerializer getSerializer(XmlRpcStreamConfig pConfig, Object pObject) throws SAXException {
        return (pObject instanceof CustomXmlRpcTypeNil)
            ? new NullSerializer()
            : super.getSerializer(pConfig, pObject);
    }
}

class test_rpc2_doc {
    public static void main(String[] cmdline)
        throws org.apache.xmlrpc.XmlRpcException,
               java.net.MalformedURLException {

        String scheme = cmdline[0];
        String domain = cmdline[1];
        String database = cmdline[2];
        String username = cmdline[3];
        String password = cmdline[4];

        //<a id=setup>
        // The following code replicates this JSON structure:
        // [{ "records":[], "context":{}, "args":[], "kwargs":{} }]
        List<Object> records = new ArrayList<>();
        Map<String, Object> context = new HashMap<>();
        List<Object> args = new ArrayList<>();
        Map<String, Object> kwargs = new HashMap<>();
        Map<String, Object> callInfo = new HashMap<>();
        List<Map> params = new ArrayList<>();
        callInfo.put("records", records);
        callInfo.put("context", context);
        callInfo.put("args", args);
        callInfo.put("kwargs", kwargs);
        params.add(callInfo);

        // custom map for create and write
        Map<String, Object> values = new HashMap<>();
        // </a>

        //<a id=common>
        URL commonUrl = new URL(String.format("%s://%s/RPC2", scheme, domain));
        XmlRpcClientConfigImpl commonConfig = new XmlRpcClientConfigImpl();
        commonConfig.setServerURL(commonUrl);
        XmlRpcClient common = new XmlRpcClient();
        common.setConfig(commonConfig);

        Map version = (Map<String, Object>)common.execute("version", emptyList());
        //</a>

        //<a id=models>
        URL modelsURL = new URL(String.format("%s://%s/RPC2?db=%s", scheme, domain, database));
        XmlRpcClientConfigImpl modelsConfig = new XmlRpcClientConfigImpl();
        modelsConfig.setServerURL(modelsURL);
        modelsConfig.setBasicUserName(username);
        modelsConfig.setBasicPassword(password);
        XmlRpcClient models = new XmlRpcClient();
        CustomXmlRpcTypeNil modelsCustomXmlRpcTypeNil = new CustomXmlRpcTypeNil(models);
        models.setTypeFactory(modelsCustomXmlRpcTypeNil);
        models.setConfig(modelsConfig);

        models.execute("system.noop", emptyList());
        //</a>

        //<a id=check_access_rights>
        args.add("read");
        kwargs.put("raise_exception", false);
        boolean canAccess = (boolean) models.execute(
            "res.partner.check_access_rights", params);
        args.clear();
        kwargs.clear();
        //</a>

        //<a id=list>
        kwargs.put("domain", asList(asList("is_company", "=", false)));
        Object[] recordIds1 = (Object[]) models.execute(
            "res.partner.search", params);
        kwargs.clear();
        //</a>

        //<a id=pagination>
        // Map<String, Object> kwargs = new HashMap<>();
        kwargs.put("domain", asList(asList("is_company", "=", false)));
        kwargs.put("offset", 10);
        kwargs.put("limit", 5);
        Object[] recordIds2 = (Object[]) models.execute(
            "res.partner.search", params);
        kwargs.clear();
        //</a>

        //<a id=count>
        kwargs.put("domain", asList(asList("is_company", "=", false)));
        int count = (int) models.execute(
            "res.partner.search_count", params);
        kwargs.clear();
        //</a>

        //<a id=search_read>
        kwargs.put("domain", asList(asList("is_company", "=", false)));
        kwargs.put("fields", asList("name", "title", "parent_name"));
        kwargs.put("limit", 1);
        Map recordData1 = (Map<String, Object>) ((Object[]) models.execute(
            "res.partner.search_read", params))[0];
        kwargs.clear();
        //</a>

        //<a id=read>
        records.add(recordIds1[0]);
        kwargs.put("fields", asList("name", "title", "parent_name"));
        Map recordData2 = (Map<String, Object>) ((Object[]) models.execute(
            "res.partner.read", params))[0];
        records.clear();
        kwargs.clear();
        //</a>

        //<a id=fields_get>
        kwargs.put("attributes", asList("type", "string"));
        Map fields = (Map<String, Map<String, Object>>) models.execute(
            "res.bank.fields_get", params);
        kwargs.clear();
        //</a>

        //<a id=create>
        values.put("name", "New Partner");
        args.add(values);
        Object[] newRecordIds = (Object[]) models.execute(
            "res.partner.create", params);
        values.clear();
        args.clear();
        //</a>

        //<a id=write>
        records.addAll(asList(newRecordIds));
        values.put("name", "Newer Partner");
        args.add(values);
        models.execute("res.partner.write", params);
        values.clear();
        args.clear();
        // get record name after having changed it
        Object[] recordsName = (Object[]) models.execute(
            "res.partner.name_get", params);
        records.clear();
        //</a>

        //<a id=unlink>
        records.addAll(asList(newRecordIds));
        models.execute("res.partner.unlink", params);
        // check if the deleted record is still in the database
        Object[] recordIds3 = (Object[]) models.execute(
            "res.partner.exists", params);
        records.clear();
        //</a>

        //<a id=ir.model>
        values.put("name", "Custom Model");
        values.put("model", "x_custom_model");
        values.put("state", "manual");
        args.add(values);
        int xCustomModelId = (int) ((Object[]) models.execute(
            "ir.model.create", params))[0];
        values.clear();
        args.clear();

        // grant the admin CRUD operations
        args.add("base");
        args.add("group_system");
        int systemGroupId = (int) ((Object[]) models.execute(
            "ir.model.data.check_object_reference", params))[1];
        args.clear();

        values.put("name", "access_x_custom_model_admin");
        values.put("model_id", xCustomModelId);
        values.put("group_id", systemGroupId);
        values.put("perm_read", true);
        values.put("perm_write", true);
        values.put("perm_create", true);
        values.put("perm_unlink", true);
        args.add(values);
        models.execute("ir.model.access.create", params);
        values.clear();
        args.clear();

        // get the fields of our newly created model
        kwargs.put("attributes", asList("type", "string"));
        Map xCustomModelFields = (Map<String, Map<String, Object>>) models.execute(
            "x_custom_model.fields_get", params);
        kwargs.clear();
        //</a>

        //<a id=ir.model.fields>
        // Add a new field "x_foo" on "x_custom_model"
        values.clear();
        values.put("model_id", xCustomModelId);  // above example
        values.put("name", "x_foo");
        values.put("ttype", "char");
        values.put("state", "manual");
        args.add(values);
        models.execute("ir.model.fields.create", params);
        values.clear();
        args.clear();

        // Create a new record and read it
        // Map<String, Object> createData = new HashMap<>();
        values.put("x_foo", "test record");
        args.add(values);
        Object[] xRecordIds = (Object[]) models.execute(
            "x_custom_model.create", params);
        values.clear();
        args.clear();

        records.addAll(asList(xRecordIds));
        kwargs.put("fields", asList("x_foo"));
        Map xRecordData = (Map<String, Object>) ((Object[]) models.execute(
            "x_custom_model.read", params))[0];
        kwargs.clear();
        //</a>
    }
}
