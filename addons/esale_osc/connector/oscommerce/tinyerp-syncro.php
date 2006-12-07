<?php
////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////// 												////////////////////
///////////////////////		PLEASE CONFIGURE THE RIGHT INCLUDES FOR YOUR CONFIGURATION		////////////////////

	include("xmlrpcutils/xmlrpc.inc");
	include("xmlrpcutils/xmlrpcs.inc");
	include("../includes/configure.php");
////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

	$con = mysql_pconnect(DB_SERVER, DB_SERVER_USERNAME, DB_SERVER_PASSWORD);
	mysql_select_db(DB_DATABASE);

	function get_taxes() {
		$taxes=array();
		
		$result=mysql_query("select tax_class_id, tax_class_title from tax_class;");
		if ($result) while ($row=mysql_fetch_row($result)) {
			$taxes[]=new xmlrpcval(array(new xmlrpcval($row[0], "int"), new xmlrpcval($row[1], "string")), "array");
		}
		return new xmlrpcresp( new xmlrpcval($taxes, "array"));
	} 

	function get_languages() {
		$languages=array();
		
		$result=mysql_query("select languages_id, name from languages;");
		if ($result) while ($row=mysql_fetch_row($result)) {
			$languages[]=new xmlrpcval(array(new xmlrpcval($row[0], "int"), new xmlrpcval($row[1], "string")), "array");
		}
		return new xmlrpcresp( new xmlrpcval($languages, "array"));
	}

	function get_categories() {
		$categories=array();
		
		$result=mysql_query("select categories_id, min(language_id) from categories_description group by categories_id;");
		if ($result) while ($row=mysql_fetch_row($result)) {
			$resultb=mysql_query("select categories_id, categories_name from categories_description where categories_id=".$row[0]." and language_id=".$row[1].";");
			if ($resultb and $row=mysql_fetch_row($resultb)) {
				$categories[]=new xmlrpcval(array(new xmlrpcval($row[0], "int"), new xmlrpcval(parent_category($row[0],$row[1]), "string")), "array");
			}
		}
		return new xmlrpcresp( new xmlrpcval($categories, "array"));
	}

	function parent_category($id, $name) {
		$result=mysql_query("select parent_id from categories where categories_id=".$id.";");
		if ($result && $row=mysql_fetch_row($result)) {
			if ($row[0]==0) {
				return $name;
			} else {
				$resultb=mysql_query("select min(language_id) from categories_description where categories_id=".$row[0].";");
				if ($resultb && $rowb=mysql_fetch_row($resultb)) {
					$resultb=mysql_query("select categories_name from categories_description where categories_id=".$row[0]." and language_id=".$rowb[0].";\n");
					if ($resultb && $rowb=mysql_fetch_row($resultb)) {
						$name=parent_category($row[0], $rowb[0] . " \\ ". $name);
						return $name;
					}
				}
			}
		}
		return $name;
	}

	function set_product_stock($tiny_product){
		mysql_query("update products set products_quantity=".$tiny_product['quantity']." where products_id=".$tiny_product['product_id'].";");
		mysql_query("update products set products_status=".(($tiny_product['quantity']>0)?1:0)." where products_id=".$tiny_product['product_id'].";");
		return new xmlrpcresp(new xmlrpcval(0,"int"));
	}
	
	function set_product($tiny_product){
		$lang_id=1;
		$id_exist=0;
		////////Check for existance of product_id ///////////
		$result =mysql_query("select products_id from products where (products_id=".$tiny_product['product_id'].");");
		if ($result && $row=mysql_fetch_row($result)) {
			$id_exist=1;
		}

//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////// CHECK FOR oscommerce if "DEFAULT_LANGUAGE" must not be "DEFAULT LANGUAGE" ///////////////////////////////
///////////////														//////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
		$result =mysql_query("select l.languages_id from languages as l configuration as c where
		c.configuration_key='DEFAULT_LANGUAGE' and c.configuration_value=l.code;");

		if ($result && $row=mysql_fetch_row($result)) {
			$lang_id=$row[0];
		}
		if ($tiny_product['quantity']>0) {
			$tiny_product['status']=1;
		} else {
			$tiny_product['status']=0;
		}
		if ($id_exist==0) {
			mysql_query("insert into products (products_quantity, products_model, products_price, products_weight, products_tax_class_id, products_status, products_date_added) values (".$tiny_product['quantity'].", '". $tiny_product['model']."', ".$tiny_product['price'].", ".$tiny_product['weight'].", ".$tiny_product['tax_class_id'].", ".$tiny_product['status'].", now());");
			$osc_id=mysql_insert_id();
			mysql_query("insert into products_description (products_id, language_id, products_name, products_description) values (".$osc_id.", ".$lang_id.", '".$tiny_product['name']."', '".$tiny_product['description']."');");
			mysql_query("insert into products_to_categories (categories_id, products_id) values(".$tiny_product['category_id'].",".$osc_id.");");
			foreach ($tiny_product['langs'] as $lang=>$values) {
				mysql_query("insert into products_description(products_id, language_id, products_name, products_description)
				values (".$osc_id.", ".$lang.", '".$values['name']."', '".$values['description']."');");
			}
		} else {
			$osc_id=$tiny_product['product_id'];
			foreach (array('quantity', 'price', 'weight', 'tax_class_id', 'status') as $key) {
				mysql_query("update products set products_".$key."=".$tiny_product[$key]." where products_id=".$osc_id.";");
			}
			mysql_query("update products set products_model='".$tiny_product['model']."' where products_id=".$osc_id.";");
			foreach (array('name', 'description') as $key) {
				mysql_query("update products_description set products_".$key."='".$tiny_product[$key]."' where products_id=".$osc_id." and language_id=".$lang_id.";");
			} 
			mysql_query("update products_to_categories set categories_id=".$tiny_product['category_id']." where products_id=".$osc_id.";");
			foreach ($tiny_product['langs'] as $lang=>$values) {
				mysql_query("delete from products_description where products_id=".$osc_id." and language_id=".$lang.";");
				mysql_query("insert into products_description(products_id, language_id, products_name, products_description)
				values (".$osc_id.", ".$lang.", '".$values['name']."', '".$values['description']."');");
			}
		}

		$cpt=0;
		if ($tiny_product['haspic']==1) {  
			if (file_exists('../../images/'.$cpt.'-'.$tiny_product['fname'])) {
					unlink('../../images/'.$cpt.'-'.$tiny_product['fname']); // DELETE THE EXISTING IMAGES
			}
			if ($hd=fopen('../../images/'.$cpt.'-'.$tiny_product['fname'], "w")){
				fwrite($hd, base64_decode($tiny_product['picture']));
				fclose($hd);
				mysql_query("update products set products_image='".$cpt."-".$tiny_product['fname']."' where
				products_id=".$osc_id.";");
				
			}
		}
		return new xmlrpcresp(new xmlrpcval($osc_id, "int"));
	}

	function get_saleorders($last_so) {
		$saleorders=array();
		$result=mysql_query("SELECT `orders_id` , `customers_name` , `customers_street_address` , `customers_city` , `customers_postcode` , `customers_state` , `customers_country` , `customers_telephone` , `customers_email_address` , `delivery_name` , `delivery_street_address` , `delivery_city` , `delivery_postcode` , `delivery_state` , `delivery_country` , `billing_name` , `billing_street_address` , `billing_city` , `billing_postcode` , `billing_state` , `billing_country` , `date_purchased` , `orders_status`, `customers_id` FROM `orders` where (orders_id > ".$last_so." and orders_status = 1);");

		if ($result){
			while ($row=mysql_fetch_row($result)) {
				$orderlines=array();
				$resultb=mysql_query("select products_id, products_quantity, final_price from orders_products where orders_id=".$row[0].";");
				if ($resultb){
					while ($rowb=mysql_fetch_row($resultb)) {
						$orderlines[]=new xmlrpcval( array("product_id" =>		new xmlrpcval($rowb[0], "int"),
															"product_qty" =>	new xmlrpcval($rowb[1], "int"),
															"price" =>			new xmlrpcval($rowb[2], "int")
														 ), "struct");
			 		}
				}
				$note="no note";
				$saleorders[] = new xmlrpcval( array("id" =>		new xmlrpcval( $row[0], "int"),
													"note" => 		new xmlrpcval( $note, "string" ),
													"lines" =>		new xmlrpcval( $orderlines, "array"),
													"address" =>	new xmlrpcval( array(	"name"		=> new xmlrpcval($row[1], "string"),
																							"address"	=> new xmlrpcval($row[2], "string"),
																							"city"		=> new xmlrpcval($row[3], "string"),
																							"zip"		=> new xmlrpcval($row[4], "string"),
																							"state"		=> new xmlrpcval($row[5], "string"),
																							"country"	=> new xmlrpcval($row[6], "string"),
																							"phone"		=> new xmlrpcval($row[7], "string"),
																							"email"		=> new xmlrpcval($row[8], "string"),
																							"esale_id"	=> new xmlrpcval($row[23], "string")
																						), "struct"),
													"delivery" =>	new xmlrpcval( array(	"name"		=> new xmlrpcval($row[9], "string"),
																							"address"	=> new xmlrpcval($row[10], "string"),
																							"city"		=> new xmlrpcval($row[11], "string"),
																							"zip"		=> new xmlrpcval($row[12], "string"),
																							"state"		=> new xmlrpcval($row[13], "string"),
																							"country"	=> new xmlrpcval($row[14], "string"),
																							"email"		=> new xmlrpcval($row[8], "string"),
																							"esale_id"	=> new xmlrpcval($row[23], "string")
																						), "struct"),
													"billing" =>	new xmlrpcval( array(	"name"		=> new xmlrpcval($row[15], "string"),
																							"address"	=> new xmlrpcval($row[16], "string"),
																							"city"		=> new xmlrpcval($row[17], "string"),
																							"zip"		=> new xmlrpcval($row[18], "string"),
																							"state"		=> new xmlrpcval($row[19], "string"),
																							"country"	=> new xmlrpcval($row[20], "string"),
																							"email"		=> new xmlrpcval($row[8], "string"),
																							"esale_id"	=> new xmlrpcval($row[23], "string")
																						), "struct"),
													"date" =>		new xmlrpcval( $row[21], "string")
												), "struct");
			}
		}
		return new xmlrpcresp(new xmlrpcval($saleorders, "array"));
	}


	function get_min_open_orders($last_so) {
		$result=mysql_query("SELECT min(`orders_id`) as min FROM `orders` where (orders_id <= ".$last_so.") and (orders_status = 2);");
		if ($result) {
			$min=mysql_fetch_row($result);
			return new xmlrpcresp( new xmlrpcval($min[0], "int"));
		}
		else return new xmlrpcresp( new xmlrpcval(-1, "int"));
	} 

	function close_open_orders($order_id) {
		mysql_query("update orders set orders_status=3 where orders_id=".$order_id.";");
		return new xmlrpcresp(new xmlrpcval(0, "int"));
	}


	function process_order($order_id) {
		mysql_query("update orders set orders_status=2 where orders_id=".$order_id.";");
		return new xmlrpcresp(new xmlrpcval(0, "int"));
	}

	$server = new xmlrpc_server( array(	"get_taxes" => array(		"function" => "get_taxes",
																	"signature" => array(	array($xmlrpcArray)
																						)
																	),
										"get_languages" => array(	"function" =>	"get_languages",
																	"signature" => array(	array($xmlrpcArray)
																						)
																	),
										"get_categories" => array(	"function" =>	"get_categories",
																	"signature" =>	array(	array($xmlrpcArray)
																						)
																	),
										"get_saleorders" => array(	"function" =>	"get_saleorders",
																	"signature" =>	array(	array($xmlrpcArray, $xmlrpcInt)
																						)
																	),
										"get_min_open_orders" => array(	"function" =>	"get_min_open_orders",
																	"signature" =>	array(	array($xmlrpcInt, $xmlrpcInt)
																						)
																	),
										"set_product" => array(		"function" =>	"set_product",
																	"signature" =>	array(	array($xmlrpcInt, $xmlrpcStruct)
																						)
																	),
										"set_product_stock" => array(	"function" =>	"set_product_stock",
																		"signature" =>	array(	array($xmlrpcInt, $xmlrpcStruct)
																						)
																	),
										"process_order" => array(		"function" =>	"process_order",
																		"signature" =>	array(	array($xmlrpcInt, $xmlrpcInt)
																						)
																	),
										"close_open_orders" => array(	"function" =>	"close_open_orders",
																		"signature" =>	array(	array($xmlrpcInt, $xmlrpcInt)
																						)
																	)
										), false);
	$server->functions_parameters_type= 'phpvals';
	$server->service();
?>
