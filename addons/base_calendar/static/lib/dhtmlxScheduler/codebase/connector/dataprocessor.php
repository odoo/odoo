<?php
/*! Base DataProcessor handling
**/
class DataProcessor{
	protected $connector;//!< Connector instance
	protected $config;//!< DataConfig instance
	protected $request;//!< DataRequestConfig instance
	
	/*! constructor
		
		@param connector 
			Connector object
		@param config
			DataConfig object
		@param request
			DataRequestConfig object
	*/
	function __construct($connector,$config,$request){
		$this->connector= $connector;
		$this->config=$config;
		$this->request=$request;
	}
	
	/*! convert incoming data name to valid db name
		redirect to Connector->name_data by default
		@param data 
			data name from incoming request
		@return 
			related db_name
	*/
	function name_data($data){
		return $data;
	}
	/*! retrieve data from incoming request and normalize it
		
		@param ids 
			array of extected IDs
		@return 
			hash of data
	*/
	function get_post_values($ids){
		$data=array(); 
		for ($i=0; $i < sizeof($ids); $i++)
			$data[$ids[$i]]=array();
		
		foreach ($_POST as $key => $value) {
			$details=explode("_",$key,2);
			if (sizeof($details)==1) continue;
			
			$name=$this->name_data($details[1]);
			$data[$details[0]][$name]=$value;
		}
			
		return $data;
	}
	/*! process incoming request ( save|update|delete )
	*/
	function process(){
		LogMaster::log("DataProcessor object initialized",$_POST);
		
		$results=array();

		if (!isset($_POST["ids"]))
			throw new Exception("Incorrect incoming data, ID of incoming records not recognized");
			
		$ids=explode(",",$_POST["ids"]);
		$rows_data=$this->get_post_values($ids);
		$failed=false;
		
		try{
			if ($this->connector->sql->is_global_transaction())
				$this->connector->sql->begin_transaction();
			
			for ($i=0; $i < sizeof($ids); $i++) { 
				$rid = $ids[$i];
				LogMaster::log("Row data [{$rid}]",$rows_data[$rid]);
				
				if (!isset($_POST[$rid."_!nativeeditor_status"]))
					throw new Exception("Status of record [{$rid}] not found in incoming request");
				$status = $_POST[$rid."_!nativeeditor_status"];
				
				$action=new DataAction($status,$rid,$rows_data[$rid]);
				$results[]=$action;
				$this->inner_process($action);
			}
			
		} catch(Exception $e){
			$failed=true;
		}
		
		if ($this->connector->sql->is_global_transaction()){
			if (!$failed)
				for ($i=0; $i < sizeof($results); $i++)
					if ($results[$i]->get_status()=="error" || $results[$i]->get_status()=="invalid"){
						$failed=true; 
						break;
					}
			if ($failed){
				for ($i=0; $i < sizeof($results); $i++)
					$results[$i]->error();
				$this->connector->sql->rollback_transaction();
			}
			else
				$this->connector->sql->commit_transaction();
		}
		
		$this->output_as_xml($results);
	}	
	
	/*! converts status string to the inner mode name
		
		@param status 
			external status string
		@return 
			inner mode name
	*/
	protected function status_to_mode($status){
		switch($status){
			case "updated":
				return "update";
				break;
			case "inserted":
				return "insert";
				break;
			case "deleted":
				return "delete";
				break;
			default:
				return $status;
				break;
		}
	}
	/*! process data updated request received
		
		@param action 
			DataAction object
		@return 
			DataAction object with details of processing
	*/
	protected function inner_process($action){
		
		if ($this->connector->sql->is_record_transaction())
				$this->connector->sql->begin_transaction();		
		
		try{
				
			$mode = $this->status_to_mode($action->get_status());
			if (!$this->connector->access->check($mode)){
				LogMaster::log("Access control: {$operation} operation blocked");
				$action->error();
			} else {
				$check = $this->connector->event->trigger("beforeProcessing",$action);
				if (!$action->is_ready())
					$this->check_exts($action,$mode);
				$check = $this->connector->event->trigger("afterProcessing",$action);
			}
		
		} catch (Exception $e){
			$action->set_status("error");
		}
		
		if ($this->connector->sql->is_record_transaction()){
			if ($action->get_status()=="error" || $action->get_status()=="invalid")
				$this->connector->sql->rollback_transaction();		
			else
				$this->connector->sql->commit_transaction();		
		}
				
		return $action;
	}
	/*! check if some event intercepts processing, send data to DataWrapper in other case

		@param action 
			DataAction object
		@param mode
			name of inner mode ( will be used to generate event names )
	*/
	function check_exts($action,$mode){
		$old_config = new DataConfig($this->config);
		
		$this->connector->event->trigger("before".$mode,$action);
		if ($action->is_ready())
			LogMaster::log("Event code for ".$mode." processed");
		else {
			//check if custom sql defined
			$sql = $this->connector->sql->get_sql($mode,$action);
			if ($sql)
				$this->connector->sql->query($sql);
			else{
				$action->sync_config($this->config);
				$method=array($this->connector->sql,$mode);
				if (!is_callable($method))
					throw new Exception("Unknown dataprocessing action: ".$mode);
				call_user_func($method,$action,$this->request);
			}
		}
		$this->connector->event->trigger("after".$mode,$action);
		
		$this->config = $old_config;
	}
	
	/*! output xml response for dataprocessor

		@param  results
			array of DataAction objects
	*/
	function output_as_xml($results){
		LogMaster::log("Edit operation finished",$results);
		ob_clean();
		header("Content-type:text/xml");
		echo "<?xml version='1.0' ?>";
		echo "<data>";
		for ($i=0; $i < sizeof($results); $i++)
			echo $results[$i]->to_xml();
		echo "</data>";
	}		
	
}

/*! contain all info related to action and controls customizaton
**/
class DataAction{
	private $status; //!< cuurent status of record
	private $id;//!< id of record
	private $data;//!< data hash of record
	private $userdata;//!< hash of extra data , attached to record
	private $nid;//!< new id value , after operation executed
	private $output;//!< custom output to client side code
	private $attrs;//!< hash of custtom attributes
	private $ready;//!< flag of operation's execution
	private $addf;//!< array of added fields
	private $delf;//!< array of deleted fields
	
	
	/*! constructor
		
		@param status 
			current operation status
		@param id
			record id
		@param data
			hash of data
	*/
	function __construct($status,$id,$data){
		$this->status=$status;
		$this->id=$id;
		$this->data=$data;	
		$this->nid=$id;
		
		$this->output="";
		$this->attrs=array();
		$this->ready=false;
		
		$this->addf=array();
		$this->delf=array();
	}

	
	/*! add custom field and value to DB operation
		
		@param name 
			name of field which will be added to DB operation
		@param value
			value which will be used for related field in DB operation
	*/
	function add_field($name,$value){
		LogMaster::log("adding field: ".$name.", with value: ".$value);
		$this->data[$name]=$value;
		$this->addf[]=$name;
	}
	/*! remove field from DB operation
		
		@param name 
			name of field which will be removed from DB operation
	*/
	function remove_field($name){
		LogMaster::log("removing field: ".$name);
		$this->delf[]=$name;
	}
	
	/*! sync field configuration with external object
		
		@param slave 
			SQLMaster object
		@todo 
			check , if all fields removed then cancel action
	*/
	function sync_config($slave){
		foreach ($this->addf as $k => $v)
			$slave->add_field($v);
		foreach ($this->delf as $k => $v)
			$slave->remove_field($v);
	}
	/*! get value of some record's propery
		
		@param name 
			name of record's property ( name of db field or alias )
		@return 
			value of related property
	*/
	function get_value($name){
		if (!array_key_exists($name,$this->data)){
			LogMaster::log("Incorrect field name used: ".$name);
			LogMaster::log("data",$this->data);
			return "";
		}
		return $this->data[$name];
	}
	/*! set value of some record's propery
		
		@param name 
			name of record's property ( name of db field or alias )
		@param value
			value of related property
	*/
	function set_value($name,$value){
		LogMaster::log("change value of: ".$name." as: ".$value);
		$this->data[$name]=$value;
	}
	/*! get hash of data properties
		
		@return 
			hash of data properties
	*/
	function get_data(){
		return $this->data;
	}
	/*! get some extra info attached to record
		deprecated, exists just for backward compatibility, you can use set_value instead of it
		@param name 
			name of userdata property
		@return 
			value of related userdata property
	*/
	function get_userdata_value($name){
		return $this->get_value($name);
	}
	/*! set some extra info attached to record
		deprecated, exists just for backward compatibility, you can use get_value instead of it
		@param name 
			name of userdata property
		@param value
			value of userdata property
	*/
	function set_userdata_value($name,$value){
		return $this->set_value($name,$value);
	}
	/*! get current status of record
		
		@return 
			string with status value
	*/
	function get_status(){
		return $this->status;
	}
	/*! assign new status to the record
		
		@param status 
			new status value
	*/
	function set_status($status){
		$this->status=$status;
	}
	/*! get id of current record
		
		@return 
			id of record
	*/
	function get_id(){
		return $this->id;
	}
	/*! sets custom response text
		
		can be accessed through defineAction on client side. Text wrapped in CDATA, so no extra escaping necessary
		@param text 
			custom response text
	*/
	function set_response_text($text){
		$this->set_response_xml("<![CDATA[".$text."]]>");
	}
	/*! sets custom response xml
		
		can be accessed through defineAction on client side
		@param text
			string with XML data
	*/
	function set_response_xml($text){
		$this->output=$text;
	}
	/*! sets custom response attributes
		
		can be accessed through defineAction on client side
		@param name
			name of custom attribute
		@param value
			value of custom attribute
	*/
	function set_response_attribute($name,$value){
		$this->attrs[$name]=$value;
	}
	/*! check if action finished 
		
		@return 
			true if action finished, false otherwise
	*/
	function is_ready(){
		return $this->ready;
	}	
	/*! return new id value
	
		equal to original ID normally, after insert operation - value assigned for new DB record	
		@return 
			new id value
	*/
	function get_new_id(){
		return $this->nid;
	}
	
	/*! set result of operation as error
	*/
	function error(){
		$this->status="error";
		$this->ready=true;
	}
	/*! set result of operation as invalid
	*/
	function invalid(){
		$this->status="invalid";
		$this->ready=true;
	}
	/*! confirm successful opeation execution
		@param  id
			new id value, optional
	*/
	function success($id=false){
		if ($id!==false)
			$this->nid = $id;
		$this->ready=true;
	}
	/*! convert DataAction to xml format compatible with client side dataProcessor
		@return 
			DataAction operation report as XML string
	*/
	function to_xml(){
		$str="<action type='{$this->status}' sid='{$this->id}' tid='{$this->nid}' ";
		foreach ($this->attrs as $k => $v) {
			$str.=$k."='".$v."' ";
		}
		$str.=">{$this->output}</action>";	
		return $str;
	}
	/*! convert self to string ( for logs )
		
		@return 
			DataAction operation report as plain string 
	*/
	function __toString(){
		return "action:{$this->status}; sid:{$this->id}; tid:{$this->nid};";
	}
	

}


?>