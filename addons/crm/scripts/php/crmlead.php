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
		
	function mailTo($post)
	{	
		if (!empty($post))
		{
				
			if (empty($this->to))
			{
				$this->to = 'sales@tinyerp.com';
			}
			
			if (empty($this->subject))
			{
				$this->subject = 'Contact form information';
			}

			$body = '<table width="90%" border="0" cellspacing="2" cellpadding="2">
						<tr>
								<td width="25%"></td>
								<td width="2%"></td>
								<td></td>
						</tr>';
						
			foreach ($post as $key => $value)
			{
				$body .=	"<tr>
									<td align='right'>$key</td>
									<td align='center'><b>:</b></td>
									<td align='left'>$value</td>
							</tr>";
			}

			$body .= '</table>';
			
			$header = 'MEME-version : 1.0'."\r\n";
			$header .= 'Content-type: text/html; charset=iso-8859-1'."\r\n";
			$header .= 'From: '.$post['name'].' <'.$post['email'].'>'."\r\n";
			$header .= 'Reply-To: '.$post['name'].' <'.$post['email'].'>'."\r\n";
			$header .= 'Return-Path: '.$post['name'].' <'.$post['email'].'>'."\r\n";
			
			if (mail($this->to, $this->subject, $body, $header))
			{
				echo "<br /><h3>Thank You, Your information has been successfully submitted.</h3><br /><p><b>We will be in touch very soon.</b></p>";
				
			}
			else
			{
				echo "<br /><h4>Sorry, Due to some problem Your information has not been submitted.</h4>";
			}
			
		}
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
							  "title" => new xmlrpcval($post['salutation'], "string"),
							  "email_from" => new xmlrpcval($post['email'], "string"),
							  "phone" => new xmlrpcval($post['phone'], "string"),
							  "partner_name" => new xmlrpcval($post['name'], "string"),
							  "function_name" => new xmlrpcval($post["jobtitle"], "string"),
							  "zip" => new xmlrpcval($post['zip'], "string"),
							  "stage_id" => new xmlrpcval(6, "int"),
							  "city" => new xmlrpcval($post['city'], "string"),
							  "country_id" => new xmlrpcval($countryId, "int"),
							  "state" => new xmlrpcval("draft", "string"),
							  "user_id" => new xmlrpcval(false, "boolean"),
							  "description" => new xmlrpcval("No.of Employees: ".$post['employees']."\nState: ".$post['state']."\nIndustry: ".$post['industry']."\nReasons: ".$post['reasons']."\nAbout: ".$post['about']."\nQuestions: ".stripslashes($post['questions'])."\nUpdate: ".$post['update'], "string")
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
						$val = array ( "description" => new xmlrpcval("About: ".$post['about']."\nQuestions: ".$post['questions']),
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

	$arrData = array();
	$arrData = array_merge($arrData, (array)$_POST);
	
	$cnt = new Contact('sales5@openerp.com', 'Country: '.$arrData['country']. ' About: ' .$arrData['about']);
	
	/* This function use for sending mail on perticular mail account */
	/*$cnt->mailTo($arrData); */
	
	/* This function use ceating lead in crm of opener erp database */
	$cnt->xmlCallTo('<username>', '<password>', '<db>', '<server>', $arrData);
	
	exit;
?>
