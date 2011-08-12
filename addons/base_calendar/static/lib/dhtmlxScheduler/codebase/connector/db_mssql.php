<?php
require_once("db_common.php");
/*! MSSQL implementation of DataWrapper
**/
class MsSQLDBDataWrapper extends DBDataWrapper{
	private $last_id=""; //!< ID of previously inserted record
	private $insert_operation=false; //!< flag of insert operation
	private $start_from=false; //!< index of start position
	
	public function query($sql){
		LogMaster::log($sql);
		$res = mssql_query($sql,$this->connection);
		if ($this->insert_operation){
			$last = mssql_fetch_assoc($res);
			$this->last_id = $last["dhx_id"];
			mssql_free_result($res);
		}
		if ($this->start_from)
			mssql_data_seek($res,$this->start_from);
		return $res;
	}
	
	public function get_next($res){
		return mssql_fetch_assoc($res);
	}
	
	protected function get_new_id(){
		/*
		MSSQL doesn't support identity or auto-increment fields
		Insert SQL returns new ID value, which stored in last_id field
		*/
		return $this->last_id;
	}
	
	protected function insert_query($data,$request){
		$sql = parent::insert_query($data,$request);
		$this->insert_operation=true;
		return $sql.";SELECT @@IDENTITY AS dhx_id";
	}		
	
	protected function select_query($select,$from,$where,$sort,$start,$count){
		$sql="SELECT " ;
		if ($count)
			$sql.=" TOP ".($count+$start);
		$sql.=" ".$select." FROM ".$from;
		if ($where) $sql.=" WHERE ".$where;
		if ($sort) $sql.=" ORDER BY ".$sort;
		if ($start && $count) 
			$this->start_from=$start;
		else 
			$this->start_from=false;
		return $sql;
	}

	public function escape($data){
		/*
		there is no special escaping method for mssql - use common logic
		*/
		return str_replace("'","''",$data);
	}
	
	public function begin_transaction(){
		$this->query("BEGIN TRAN");
	}
}
?>