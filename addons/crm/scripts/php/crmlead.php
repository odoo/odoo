<?php

    include("xmlrpc.inc");      

class Contact
{
    private $subject = '', $to = '';
    
    function __construct($to, $sub)
    {
        $this->to = $to;
        $this->subject = $sub;
    }
        

    function xmlCallTo($usr, $password, $database, $server, $post)
    {
        $user = $usr;
        $pass = $password;
        $db = $database;
        $server_url = $server; //'http://localhost:8069/xmlrpc/'
        
        $client = new xmlrpc_client($server_url.'common');
        
        $msg = new xmlrpcmsg('login');
        $msg->addParam(new xmlrpcval($db, "string"));
        $msg->addParam(new xmlrpcval($user, "string"));
        $msg->addParam(new xmlrpcval($pass, "string"));


        $res =  &$client->send($msg);
        
        if(!$res->faultCode()){
            
            $val = $res->value();   
            $id = $val->scalarval();

            if (empty($id)){
                
                echo "Connection error = ";
                exit;
            }
            else
            {
                $client2 = new xmlrpc_client($server_url.'object');
                $key = array(new xmlrpcval(array(new xmlrpcval("code", "string"), new xmlrpcval("=", "string"), new xmlrpcval($post['country'], "string")),"array"),);
                $msg = new xmlrpcmsg('execute');
                $msg->addParam(new xmlrpcval($db, "string"));
                $msg->addParam(new xmlrpcval($id, "int"));
                $msg->addParam(new xmlrpcval($pass, "string"));
                $msg->addParam(new xmlrpcval("res.country","string"));
                $msg->addParam(new xmlrpcval("search", "string"));
                $msg->addParam(new xmlrpcval($key, "array"));
                $msg->addParam(new xmlrpcval(0, "int"));
                $msg->addParam(new xmlrpcval(1, "int"));
                
                $res = &$client2->send($msg);
                
                $val = $res->value()->scalarval();
                
                $countryId = $val[0]->scalarval();
                
                $val = array ("name" => new xmlrpcval($post['company'],"string"),
                              "email_from" => new xmlrpcval($post['email'], "string"),
                              "phone" => new xmlrpcval($post['phone'], "string"),
                              "partner_name" => new xmlrpcval($post['name'], "string"),
                              "function" => new xmlrpcval($post["jobtitle"], "string"),
                              "zip" => new xmlrpcval($post['zip'], "string"),
                              "stage_id" => new xmlrpcval(2, "int"),
                              "city" => new xmlrpcval($post['city'], "string"),
                              "country_id" => new xmlrpcval($countryId, "int"),
                              "state" => new xmlrpcval("draft", "string"),
                              "user_id" => new xmlrpcval(false, "boolean"),
                              "description" => new xmlrpcval("No.of Employees: ".$post['employees']."\nState: ".$post['state']."\nIndustry: ".$post['industry']."\nAbout: ".$post['about'], "string")
                            );
                                                
                $msg = new xmlrpcmsg('execute');
                $msg->addParam(new xmlrpcval($db, "string"));
                $msg->addParam(new xmlrpcval($id, "int"));
                $msg->addParam(new xmlrpcval($pass, "string"));
                $msg->addParam(new xmlrpcval("crm.lead", "string"));
                $msg->addParam(new xmlrpcval("create", "string"));
                $msg->addParam(new xmlrpcval($val, "struct"));
                                
                
                $res2 = &$client2->send($msg);
                
                if(!$res2->faultCode())
                {
                    $readVal = $res2->value()->scalarval();
                    
                    if (!empty($readVal))
                    {
                        $val = array ( "description" => new xmlrpcval("About: ".$post['about']),
                                "model_id" => new xmlrpcval(276, "int"),
                                "res_id" => new xmlrpcval($readVal,"int"),
                                "email_from" => new xmlrpcval($post['email'], "string"),
                                "email_to" => new xmlrpcval("sales@openerp.com", "string")
                                );

                        
                        $msg = new xmlrpcmsg('execute');
                        $msg->addParam(new xmlrpcval($db, "string"));
                        $msg->addParam(new xmlrpcval($id, "int"));
                        $msg->addParam(new xmlrpcval($pass, "string"));
                        $msg->addParam(new xmlrpcval("crm.case.history", "string"));
                        $msg->addParam(new xmlrpcval("create", "string"));
                        $msg->addParam(new xmlrpcval($val, "struct"));
                        
                        $res2 = &$client2->send($msg);

                        //echo "<br />Successfully created lead";
                        echo "<br /><h3>Thank You for your interest in openerp, we'll respond to your request shortly.</h3><br />";
                        if(strstr($post["about"],"Book")) {
                            echo '<script>window.location="http://www.openerp.com/index.php?option=com_content&amp;id=54"</script>';
                        }
                    }
                    else
                    {
                        echo "<br />Lead is not created";
                    }
                }
                else
                {
                    echo "<br />Problem in message sending for create lead";
                }
            }           
        }
        else
        {
            echo "<br />Connection not established";
        }
    }
}

    if(isset($_POST['country']) && $_POST['country'] != '') {
        $arrData = array();
        $arrData = array_merge($arrData, (array)$_POST);
        
        $cnt = new Contact('sales5@openerp.com', 'Country: '.$arrData['country']. ' About: ' .$arrData['about']);
        
        /* This function use for sending mail on perticular mail account */
        /*$cnt->mailTo($arrData); */
        
        /* This function use ceating lead in crm of opener erp database */
        //Change to fit your configuration
        $cnt->xmlCallTo('admin', 'a', 'db_1', 'http://localhost:8069/xmlrpc/', $arrData);
    }
    else {
        echo 'please fill the form at <a href="form.php">form.php</a>';
    }
    
    exit;
?>

