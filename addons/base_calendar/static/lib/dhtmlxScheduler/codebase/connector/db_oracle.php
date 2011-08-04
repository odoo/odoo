<?php
require_once("db_common.php");
/*! Implementation of DataWrapper for Oracle
**/
class OracleDBDataWrapper extends DBDataWrapper{
	private $last_id=""; //id of previously inserted record
	private $insert_operation=false; //flag of insert operation
	
	public function query($sql){
		LogMaster::log($sql);
		$stm = oci_parse($this->connection,$sql);
		if ($stm===false) throw new Exception("Oracle - sql parsing failed\n".oci_error($this->connection));
		
		$out = array(0=>null);
		if($this->insert_operation){
			oci_bind_by_name($stm,":outID",$out[0],999);
			$this->insert_operation=false;
		}
		
		
		$mode = ($this->is_record_transaction() || $this->is_global_transaction())?OCI_DEFAULT:OCI_COMMIT_ON_SUCCESS;
		$res=oci_execute($stm,$mode);
		if ($res===false) throw new Exception("Oracle - sql execution failed\n".oci_error($this->connection));
		
		$this->last_id=$out[0];
		
		return $stm;
	}
	
	public function get_next($res){
		$data = oci_fetch_assoc($res);
		if (array_key_exists("VALUE",$data))
			$data["value"]=$data["VALUE"];
		return $data;
	}
	
	protected function get_new_id(){
		/*
		Oracle doesn't support identity or auto-increment fields
		Insert SQL returns new ID value, which stored in last_id field
		*/
		return $this->last_id;
	}
	
	protected function insert_query($data,$request){
		$sql = parent::insert_query($data,$request);
		$this->insert_operation=true;
		return $sql." returning ".$this->config->id["db_name"]." into :outID";
	}		
	
	protected function select_query($select,$from,$where,$sort,$start,$count){
		$sql="SELECT ".$select." FROM ".$from;
		if ($where) $sql.=" WHERE ".$where;
		if ($sort) $sql.=" ORDER BY ".$sort;
		if ($start || $count) 
			$sql="SELECT * FROM ( select /*+ FIRST_ROWS(".$count.")*/dhx_table.*, ROWNUM rnum FROM (".$sql.") dhx_table where ROWNUM <= ".($count+$start)." ) where rnum >".$start;
		return $sql;
	}

	public function escape($data){
		/*
		as far as I can see the only way to escape data is by using oci_bind_by_name
		while it is neat solution in common case, it conflicts with existing SQL building logic
		fallback to simple escaping
		*/
		return str_replace("'","''",$data);
	}
	
	public function begin_transaction(){
		//auto-start of transaction
	}
	public function commit_transaction(){
		oci_commit($this->connection);
	}
	public function rollback_transaction(){
		oci_rollback($this->connection);
	}	
}
?>