<?
	function debug($str)
	{
		$fp = fopen('/tmp/debug_tinyerp.txt', 'a');
		fwrite($fp, $str."\n");
		fclose($fp);
	}

	// Check module name
	if (strcmp(substr($_FILES['module']['name'],-4,4),'.zip')) {
		return '0';
	}

    $port=mysql_connect(":/var/run/mysqld/mysqld.sock","tiny","XXXX");
	// Verify user and password
	$query = mysql_db_query("tiny_terp", "select id,password from jos_users where username='".addslashes($_POST['login'])."' and password=md5('".addslashes($_POST['password'])."')");
	$user = mysql_fetch_object($query);
	if (!$user) {
		return "0";
	}

	// Verify module owner
	$query = mysql_db_query("tiny_terp", "select user_id from jos_mt_links where cust_7='".addslashes($_POST['module_name'])."'");
	$row = mysql_fetch_object($query);

	if ((!$row) or $row[0]==$user[0]) {
		// save .zip module
		$dest = '/home/tiny/www/tinyerp.com/download/modules/'.$_FILES['module']['name'];
		if(move_uploaded_file($_FILES['module']['tmp_name'], $dest)) {
		} else{
		}

    }
?>
