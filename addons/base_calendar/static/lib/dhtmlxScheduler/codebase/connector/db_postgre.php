<?php
require_once("db_common.php");
/*! Implementation of DataWrapper for PostgreSQL
**/
class PostgreDBDataWrapper extends DBDataWrapper{
	public function query($sql){
		LogMaster::log($sql);
		
		$res=pg_query($this->connection,$sql);
		if ($res===false) throw new Exception("Postgre - sql execution failed\n".pg_last_error($this->connection));
		
		return $res;
	}
	
	protected function select_query($select,$from,$where,$sort,$start,$count){
		$sql="SELECT ".$select." FROM ".$from;
		if ($where) $sql.=" WHERE ".$where;
		if ($sort) $sql.=" ORDER BY ".$sort;
		if ($start || $count) 
			$sql.=" OFFSET ".$start." LIMIT ".$count;
		return $sql;
	}
		
	public function get_next($res){
		return pg_fetch_assoc($res);
	}
	
	protected function get_new_id(){
		$res  = pg_query( $this->connection, "SELECT LASTVAL() AS seq");
		$data = pg_fetch_assoc($res);
				pg_free_result($res);
		return $data['seq'];
	}
	
	public function escape($data){
		//need to use oci_bind_by_name
		return pg_escape_string($this->connection,$data);
	}

	public function tables_list() {
		$sql = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'";
		$res = pg_query($this->connection, $sql);
		$tables = array();
		while ($table = pg_fetch_assoc($res)) {
			$tables[] = $table['table_name'];
		}
		return $tables;
	}

	public function fields_list($table) {
		$sql = "SELECT * FROM information_schema.constraint_column_usage";
		$result = pg_query($this->connection, $sql);
		$field = pg_fetch_assoc($result);
		$id = $field['column_name'];

		$sql = "SELECT * FROM information_schema.columns WHERE table_name ='".$table."';";
		$result = pg_query($this->connection, $sql);
		$fields = array();
        $id = "";
		while ($field = pg_fetch_assoc($result)) {
		    $fields[] = $field["column_name"];
		}
		return array('fields' => $fields, 'key' => $id );
	}
}
?>