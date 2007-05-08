<?
	$port=mysql_connect(":/var/run/mysqld/mysqld.sock","tiny","XXXX");
	if (! $_GET['module']) {
		$query = mysql_db_query("tiny_terp", "select c1.cat_id as cat_id,c1.cat_name as name1,c2.cat_name as name2 from jos_mt_cats c1 left join jos_mt_cats c2 on (c1.cat_parent=c2.cat_id) where c1.cat_allow_submission order by c1.cat_parent,c1.ordering");
		while ($row = mysql_fetch_object($query))
			echo $row->cat_id."=".$row->name2.'/'.$row->name1."\n";
	} else {
		$query = mysql_db_query("tiny_terp", "select link_id from jos_mt_links where cust_7='".addslashes($_GET['module'])."'");
		if ($row = mysql_fetch_object($query))
			echo $row->link_id."\n";
		else
			echo "0\n";
	}
?>
