<?php

require_once("db_common.php");

class MySQLiDBDataWrapper extends MySQLDBDataWrapper{

	public function query($sql){
		LogMaster::log($sql);
		$res = $this->connection->query($sql);
		if ($res===false) throw new Exception("MySQL operation failed\n".$this->connection->error);
		return $res;
	}

	public function get_next($res){
		return $res->fetch_assoc();
	}

	protected function get_new_id(){
		return $this->connection->insert_id;
	}

	public function escape($data){
		return $this->connection->real_escape_string($data);
	}

	public function tables_list() {
		$result = $this->connection->query("SHOW TABLES");
		if ($result===false) throw new Exception("MySQL operation failed\n".$this->connection->error);

		$tables = array();
		while ($table = $result->fetch_array()) {
			$tables[] = $table[0];
		}
		return $tables;
	}

	public function fields_list($table) {
		$result = $this->connection->query("SHOW COLUMNS FROM `".$table."`");
		if ($result===false) throw new Exception("MySQL operation failed\n".$this->connection->error);
		$fields = array();
		while ($field = $result->fetch_array()) {
			if ($field['Key'] == "PRI") {
				$fields[$field[0]] = 1;
			} else {
				$fields[$field[0]] = 0;
			}
		}
		return $fields;
	}

}

?>