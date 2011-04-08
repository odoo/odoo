<?php

$str = "<data>";

for ($i=1; $i <= 100; $i++) { 
	$sales = rand(100,1000);
	$year = rand(1996,2009);
	$company = "Company ".rand(1,3);
	$str.="<item id='{$i}' sales='{$sales}' year='{$year}' company='{$company}'></item>";
}

$str .= "</data>";

file_put_contents("stat.xml",$str);

?>