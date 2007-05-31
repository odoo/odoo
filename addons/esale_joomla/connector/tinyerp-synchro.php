<?php

	define( '_VALID_MOS', 1);
	
	include("xmlrpc.inc");
	include("xmlrpcs.inc");

	require_once( 'configuration.php' );
	require_once( 'includes/joomla.php' );
	require_once( 'administrator/components/com_virtuemart/virtuemart.cfg.php' );

	$con = mysql_pconnect($mosConfig_host, $mosConfig_user,$mosConfig_password );
	mysql_select_db($mosConfig_db);

	function get_taxes() {
		global $mosConfig_dbprefix;
		$taxes=array();
		
		$result=mysql_query("select tax_rate_id, tax_rate*100 from ".$mosConfig_dbprefix."vm_tax_rate;");
		if ($result) while ($row=mysql_fetch_row($result)) {
			$taxes[]=new xmlrpcval(array(new xmlrpcval($row[0], "int"), new xmlrpcval("Tax ".$row[1]."%", "string")), "array");
		}
		return new xmlrpcresp( new xmlrpcval($taxes, "array"));
	} 

	function get_languages() {
		$languages=array();
		
		$languages[]=new xmlrpcval(array(new xmlrpcval(1, "int"), new xmlrpcval("Unique", "string")), "array");
		return new xmlrpcresp( new xmlrpcval($languages, "array"));
	}

	function get_categories() {
		global $mosConfig_dbprefix;
		$categories=array();
		
		$result=mysql_query("select category_id, category_name from ".$mosConfig_dbprefix."vm_category;");
		if ($result) while ($row=mysql_fetch_row($result)) {
			$categories[]=new xmlrpcval(array(new xmlrpcval($row[0], "int"), new xmlrpcval(parent_category($row[0],$row[1]), "string")), "array");
		}
		return new xmlrpcresp( new xmlrpcval($categories, "array"));
	}

	function parent_category($id, $name) {
		global $mosConfig_dbprefix;
		$result=mysql_query("select category_parent_id from ".$mosConfig_dbprefix."vm_category_xref where category_child_id=".$id.";");
		if ($result && $row=mysql_fetch_row($result)) {
			if ($row[0]==0) {
				return $name;
			} else {
				$resultb=mysql_query("select category_name from ".$mosConfig_dbprefix."vm_category where category_id=".$row[0].";");
				if ($resultb && $rowb=mysql_fetch_row($resultb)) {
					$name=parent_category($row[0], $rowb[0] . " \\ ". $name);
					return $name;
				}
			}
		}
		return $name;
	}

	function set_product_stock($tiny_product) {
		global $mosConfig_dbprefix;
		mysql_query("update ".$mosConfig_dbprefix."vm_product set product_in_stock=".$tiny_product['quantity']." where
		product_id=".$tiny_product['esale_joomla_id'].";");
		//mysql_query("update products set products_status=".(($tiny_product['quantity']>0)?1:0)." where
		//products_id=".$tiny_product['esale_joomla_id'].";");
		return new xmlrpcresp(new xmlrpcval(1,"int"));
	}
	

	function set_product_category($category_id, $product_ids) {

	  global $mosConfig_dbprefix;
		
	  foreach($product_ids as $key => $value){
		$result = mysql_query("select count(*) from ".$mosConfig_dbprefix."vm_product_category_xref where category_id=".$category_id." and product_id=".$value.";");
		$row = mysql_fetch_row($result);
		if (! $row[0] ){
		  mysql_query("insert into ".$mosConfig_dbprefix."vm_product_category_xref values (".$category_id.", ".$value.", NULL);");
		}
	  }
	  return new xmlrpcresp(new xmlrpcval(1,"int"));

	}

	function unpublish_product($product_ids){
		global $mosConfig_dbprefix;
		mysql_query("update ".$mosConfig_dbprefix."vm_product set product_publish='N' where product_id in (".implode(",",$product_ids).");");
		return new xmlrpcresp(new xmlrpcval(1,"int"));
	}

	function debug($s) {
		$fp = fopen("/tmp/debug.xmlrpc.txt","a");
		fwrite($fp, $s."\n");
		fclose($fp);
	}


	function set_product($tiny_product){
		global $mosConfig_dbprefix;
		$prod = Array(
			'vendor_id'=>0
		);

		$result=mysql_query("select vendor_id, vendor_currency from ".$mosConfig_dbprefix."vm_vendor;");
		if ($result && $row=mysql_fetch_row($result)) {
			$prod['vendor_id']=$row[0];
			$prod['vendor_currency']=$row[1];
		}
		$result=mysql_query("select shopper_group_id from ".$mosConfig_dbprefix."vm_shopper_group where vendor_id=".$vendor_id." and shopper_group_name='-default-';");
		if ($result && $row=mysql_fetch_row($result))
			$prod['shopper_group']=$row[0];
		if ( $tiny_product['esale_joomla_id']) {
			$result = mysql_query("select count(*) from ".$mosConfig_dbprefix."vm_product where product_id=". $tiny_product['esale_joomla_id']);
			$row = mysql_fetch_row($result);
			if (! $row[0] )
				$tiny_product['esale_joomla_id'] = 0;
		}

		if (! $tiny_product['esale_joomla_id']) {
			mysql_query("insert into ".$mosConfig_dbprefix."vm_product () values ()");
			$osc_id=mysql_insert_id();
			mysql_query("insert into ".$mosConfig_dbprefix."vm_product_price (product_id, product_price, product_currency, product_price_vdate, product_price_edate, shopper_group_id) values (".$osc_id.", ".$tiny_product['price'].", '".$vendor_currency."', 0, 0, ".$shopper_group.");");
			mysql_query("insert into ".$mosConfig_dbprefix."vm_product_category_xref (product_id, category_id) values (".$osc_id.", ".$tiny_product['category_id'].");");
		} else {
			$osc_id=$tiny_product['esale_joomla_id'];
		}

		mysql_query("update ".$mosConfig_dbprefix."vm_product set ".
			"product_in_stock=".$tiny_product['quantity'].",".
			"product_weight=".$tiny_product['weight'].",".
			"product_tax_id=".$tiny_product['tax_class_id'].",".
			"product_sku='".mysql_escape_string($tiny_product['model'])."',".
			"product_name='".mysql_escape_string($tiny_product['name'])."',".
			"vendor_id='".$prod['vendor_id']."',".
			"product_desc='".mysql_escape_string($tiny_product['description'])."', ".
			"product_publish='Y',".
			"product_s_desc='".mysql_escape_string(substr($tiny_product['description'],0,200))."' ".
			"where product_id=".$osc_id.";");

			// Replace or
			// Delete old values

		mysql_query("update ".$mosConfig_dbprefix."vm_product_price set product_price='".$tiny_product['price']."' where product_id=".$osc_id.";");
		mysql_query("update ".$mosConfig_dbprefix."vm_product_category set category_id='".$tiny_product['category_id']."' where product_id=".$osc_id.";");

		if ($tiny_product['haspic']==1) {
			$filename=tempnam('components/com_virtuemart/shop_image/product/', 'tiny_');
			$extension=strrchr($tiny_product['fname'],'.');
			$filename.=$extension;
			//file_put_contents($filename, base64_decode($tiny_product['picture']));
			$hd=fopen($filename, "w");
			fwrite($hd, base64_decode($tiny_product['picture']));
			fclose($hd);
			$short=strrchr($filename,'/');
			$short=substr($short, 1, strlen($short));
			mysql_query("update ".$mosConfig_dbprefix."vm_product set product_full_image='".$short."' where product_id=".$osc_id.";");
			$newxsize = PSHOP_IMG_WIDTH;
			if (!$newxsize) {
				$newxsize=90;
			}
			$newysize = PSHOP_IMG_HEIGHT;
			if (!$newysize) {
				$newysize=60;
			}
			$extension=strtolower($extension);
			if (in_array($extension, array('.jpeg', '.jpe', '.jpg', '.gif', '.png'))) {
				if (in_array($extension, array('.jpeg', '.jpe', '.jpg'))) {
					$extension='.jpeg';
				}
				$thumb=tempnam('components/com_virtuemart/shop_image/product/', 'tiny_').$extension;
				$load='imagecreatefrom'.substr($extension,1,strlen($extension)-1);
				$save='image'.substr($extension,1,strlen($extension)-1);
				$tmp_img=$load($filename);
				$imgsize = getimagesize($filename);
				if ($imgsize[0] > $newxsize || $imgsize[1] > $newysize) {
					if ($imgsize[0]*$newysize > $imgsize[1]*$newxsize) {
						$ratio=$imgsize[0]/$newxsize;
					} else {
						$ratio=$imgsize[1]/$newysize;
					}
				} else {
					$ratio=1;
				}
				$tn=imagecreatetruecolor (floor($imgsize[0]/$ratio),floor($imgsize[1]/$ratio));
				imagecopyresized($tn,$tmp_img,0,0,0,0,floor($imgsize[0]/$ratio),floor($imgsize[1]/$ratio),$imgsize[0],$imgsize[1]);
				$short=strrchr($thumb,'/');
				$short=substr($short,1,strlen($short));
				$save($tn, $thumb);
				mysql_query("update ".$mosConfig_dbprefix."vm_product set product_thumb_image='".$short."' where product_id=".$osc_id.";");
			}
		}
		return new xmlrpcresp(new xmlrpcval($osc_id, "int"));
	}

	function get_saleorders($last_so) {
		global $mosConfig_dbprefix;
		$saleorders=array();

		$result=mysql_query(
			"SELECT
				o.`order_id`, c.`last_name`, c.`address_1`, c.`city`, c.`zip`, c.`state`,
				c.`country`, c.`phone_1`, c.`user_email`, d.`last_name` , d.`address_1` ,
				d.`city`, d.`zip`, d.`state`, d.`country`, o.`cdate`,
				c.title, c.first_name, d.title, d.first_name,
				d.user_id, c.user_id, o.customer_note
			FROM ".
				$mosConfig_dbprefix."vm_orders as o,".
				$mosConfig_dbprefix."vm_user_info as c, ".
				$mosConfig_dbprefix."vm_user_info as d
			where
				o.order_id>".$last_so." and
				o.user_id=c.user_id and
				(c.address_type_name is NULL or c.address_type_name='-default-') and
				o.user_info_id=d.user_info_id;
		");

		if ($result) while ($row=mysql_fetch_row($result)) {
			$orderlines=array();
			$resultb=mysql_query("select product_id, product_quantity, product_item_price from ".$mosConfig_dbprefix."vm_order_item where order_id=".$row[0].";");
			if ($resultb) while ($rowb=mysql_fetch_row($resultb)) {
				$orderlines[]=new xmlrpcval( array(
					"product_id" => new xmlrpcval($rowb[0], "int"),
					"product_qty" =>	new xmlrpcval($rowb[1], "int"),
					"price" =>	new xmlrpcval($rowb[2], "int")
				), "struct");
			}
			$saleorders[] = new xmlrpcval( array(
				"id" => new xmlrpcval( $row[0], "int"),
				"note" => new xmlrpcval( $row[22], "string"),
				"lines" =>		new xmlrpcval( $orderlines, "array"),
				"address" =>	new xmlrpcval( array(
					"name"		=> new xmlrpcval($row[16]." ".$row[1]." ".$row[17], "string"),
					"address"	=> new xmlrpcval($row[2], "string"),
					"city"		=> new xmlrpcval($row[3], "string"),
					"zip"		=> new xmlrpcval($row[4], "string"),
					"state"		=> new xmlrpcval($row[5], "string"),
					"country"	=> new xmlrpcval($row[6], "string"),
					"phone"		=> new xmlrpcval($row[7], "string"),
					"email"		=> new xmlrpcval($row[8], "string"),
					"esale_id"	=> new xmlrpcval($row[20], "string")
				), "struct"),
				"delivery" =>	new xmlrpcval( array(
					"name"		=> new xmlrpcval($row[18]." ".$row[9]." ".$row[19], "string"),
					"address"	=> new xmlrpcval($row[10], "string"),
					"city"		=> new xmlrpcval($row[11], "string"),
					"zip"		=> new xmlrpcval($row[12], "string"),
					"state"		=> new xmlrpcval($row[13], "string"),
					"country"	=> new xmlrpcval($row[14], "string"),
					"email"		=> new xmlrpcval($row[8], "string"),
					"esale_id"	=> new xmlrpcval($row[21], "string")
				), "struct"),
				"billing" =>new xmlrpcval( array(
					"name"		=> new xmlrpcval($row[16]." ".$row[1]." ".$row[17], "string"),
					"address"	=> new xmlrpcval($row[2], "string"),
					"city"		=> new xmlrpcval($row[3], "string"),
					"zip"		=> new xmlrpcval($row[4], "string"),
					"state"		=> new xmlrpcval($row[5], "string"),
					"country"	=> new xmlrpcval($row[6], "string"),
					"email"		=> new xmlrpcval($row[8], "string"),
					"esale_id"	=> new xmlrpcval($row[20], "string")
				), "struct"),
				"date" =>		new xmlrpcval( date('YmdHis',$row[15]), "date")
			), "struct");
		}
		return new xmlrpcresp(new xmlrpcval($saleorders, "array"));
	}

	function process_order($order_id) {
		global $mosConfig_dbprefix;
		mysql_query("update ".$mosConfig_dbprefix."vm_orders set order_status='C' where order_id=".$order_id.";");
		mysql_query("update ".$mosConfig_dbprefix."vm_order_item set oerder_status='C' where order_id=".$order_id.";");
		return new xmlrpcresp(new xmlrpcval(0, "int"));
	}

	function close_order($order_id) {
		global $mosConfig_dbprefix;
		mysql_query("update ".$mosConfig_dbprefix."vm_orders set order_status='S' where order_id=".$order_id.";");
		mysql_query("update ".$mosConfig_dbprefix."vm_order_item set oerder_status='S' where order_id=".$order_id.";");
		return new xmlrpcresp(new xmlrpcval(0, "int"));
	}

	$server = new xmlrpc_server( array(
		"get_taxes" => array(
			"function" => "get_taxes",
			"signature" => array(array($xmlrpcArray))
		),
		"get_languages" => array(
			"function" => "get_languages",
			"signature" => array(array($xmlrpcArray))
		),
		"get_categories" => array(
			"function" => "get_categories",
			"signature" => array(array($xmlrpcArray))
		),
		"get_saleorders" => array(
			"function" => "get_saleorders",
			"signature" => array(array($xmlrpcArray, $xmlrpcInt))
		),
		"set_product_category" => array(
			"function" => "set_product_category",
			"signature" => array(array($xmlrpcInt, $xmlrpcInt, $xmlrpcArray))
		),
		"unpublish_product" => array(
			"function" => "unpublish_product",
			"signature" => array(array($xmlrpcInt, $xmlrpcArray))
		),
		"set_product" => array(
			"function" => "set_product",
			"signature" => array(array($xmlrpcInt, $xmlrpcStruct))
		),
		"set_product_stock" => array(
			"function" => "set_product_stock",
			"signature" => array(array($xmlrpcInt, $xmlrpcStruct))
		),
		"process_order" => array(
			"function" => "process_order",
			"signature" => array(array($xmlrpcInt, $xmlrpcInt))
		),
		"close_order" => array(
			"function" => "close_order",
			"signature" => array(array($xmlrpcInt, $xmlrpcInt))
		)
	), false);
	$server->functions_parameters_type= 'phpvals';
	$server->service();
?>
