<?php
    include("xmlrpc.inc");
    
    //Change to fit your configuration
    $user = "admin";
    $password = "a";
    $db = "db_1";
    $serverUri = "http://localhost:8069/xmlrpc/";
    
    
    $client = new xmlrpc_client($serverUri.'common');
    
    $msg = new xmlrpcmsg('login');
    $msg->addParam(new xmlrpcval($db, "string"));
    $msg->addParam(new xmlrpcval($user, "string"));
    $msg->addParam(new xmlrpcval($password, "string"));


    $res =  &$client->send($msg);

    if(!$res->faultCode()){
        
        $id = $res->value()->scalarval();   

        $client = new xmlrpc_client($serverUri.'object');

        $key = array(new xmlrpcval(array(new xmlrpcval("id", "string"),
                    new xmlrpcval(">", "string"),
                    new xmlrpcval(0, "int")),"array"),);
                    
        
                
        $msg = new xmlrpcmsg('execute');
        $msg->addParam(new xmlrpcval($db, "string"));
        $msg->addParam(new xmlrpcval($id, "int"));
        $msg->addParam(new xmlrpcval($password, "string"));
        $msg->addParam(new xmlrpcval("res.country","string"));
        $msg->addParam(new xmlrpcval("search", "string"));      
        $msg->addParam(new xmlrpcval($key, "array"));
        $msg->addParam(new xmlrpcval(0, "int"));
        $msg->addParam(new xmlrpcval(0, "int"));
        $msg->addParam(new xmlrpcval("id ASC", "string"));
        
        $res = &$client->send($msg);

        if(!$res->faultCode())
        {
            $val = $res->value()->scalarval();
            
            $ides = array();
            
            for ($i=0 ; $i<count($val); $i++)
            {
                array_push($ides, new xmlrpcval($val[$i]->scalarval(), "int"));
            }
            
            $client = new xmlrpc_client($serverUri.'object');
            
            $fields = array(new xmlrpcval("code", "string"), new xmlrpcval("name", "string"));
            
            $msg = new xmlrpcmsg('execute');
            $msg->addParam(new xmlrpcval($db, "string"));
            $msg->addParam(new xmlrpcval($id, "int"));
            $msg->addParam(new xmlrpcval($password, "string"));
            $msg->addParam(new xmlrpcval("res.country","string"));
            $msg->addParam(new xmlrpcval("read", "string"));
            $msg->addParam(new xmlrpcval($ides, "array"));
            $msg->addParam(new xmlrpcval($fields, "array"));

            $res = &$client->send($msg);
            
            if (!$res->faultCode())
            {
                $val = $res->value()->scalarval();
                
                $select ='<select class="inputbox required"  name="country" id="country" >                                  
                            <option value="" selected="selected"> -- Select an Option -- </option>';

                for ($i=0; $i<count($val);$i++)
                {
                    $field = $val[$i]->scalarval();
                    $select .= '<option value="'.$field['code']->scalarval().'">'.$field['name']->scalarval().'</option>';
                }
                
                $select .= '</select>';
                
                echo $select;
            }
            else
            {
                echo "Country not getting";
            }
        }
        else
        {
            echo "Country list id empty";
        }       
    }
    else
    {
        echo "connection not establish";
    }


?>
