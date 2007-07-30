<?
	function debug($str)
	{
		$fp = fopen('/tmp/debug_tinyerp.txt', 'a');
		fwrite($fp, $str."\n");
		fclose($fp);
	}

    $port=mysql_connect(":/var/run/mysqld/mysqld.sock","tiny","XXXX");
	// Verify user and password
	$query = mysql_db_query("tiny_terp", "select id,password from jos_users where username='".addslashes($_POST['login'])."' and password=md5('".addslashes($_POST['password'])."')");
	$user = mysql_fetch_object($query);
	if (!$user) {
		echo "1\n";
		return;
	}

	// Verify module owner
	$query = mysql_db_query("tiny_terp", "select user_id from jos_mt_links where cust_7='".addslashes($_POST['module_name'])."'");
	$row = mysql_fetch_object($query);

	if ((!$row) or $row[0]==$user[0]) {
		// save .zip module
		$dest = '/home/tiny/www/tinyerp.com/download/modules/'.$_FILES['module']['name'];
		if (!file_exists($dest)) {
			if(move_uploaded_file($_FILES['module']['tmp_name'], $dest)) {
				echo "0\n";
				return;
			} else{
				echo "3\n";
				return;
			}
		} else {
			echo "2\n";
			return;
		}
	}
?>
