<?php

require_once("tools.php");
require_once("db_common.php");
require_once("dataprocessor.php");
require_once("update.php");

//enable buffering to catch and ignore any custom output before XML generation
//because of this command, it strongly recommended to include connector's file before any other libs
//in such case it will handle any extra output from not well formed code of other libs
ini_set("output_buffering","On");
ob_start();

class OutputWriter{
	private $start;
	private $end;
	private $type;
	
	public function __construct($start, $end = ""){
		$this->start = $start;
		$this->end = $end;
		$this->type = "xml";
	}
	public function add($add){
		$this->start.=$add;
	}
	public function reset(){
		$this->start="";
		$this->end="";
	}
	public function set_type($add){
		$this->type=$add;
	}
	public function output($name="", $inline=true){
		ob_clean();
		if ($this->type == "xml")
			header("Content-type: text/xml");
			
		echo $this->__toString();
	}
	public function __toString(){
		return $this->start.$this->end;
	}
}

/*! EventInterface
	Base class , for iterable collections, which are used in event
**/
class EventInterface{ 
	protected $request; ////!< DataRequestConfig instance
	public $rules=array(); //!< array of sorting rules
	
	/*! constructor
		creates a new interface based on existing request
		@param request 
			DataRequestConfig object
	*/
	public function __construct($request){
		$this->request = $request;
	}

	/*! remove all elements from collection
		*/	
	public function clear(){
		array_splice($rules,0);
	}
	/*! get index by name
		
		@param name 
			name of field
		@return 
			index of named field
	*/
	public function index($name){
		$len = sizeof($this->rules);
		for ($i=0; $i < $len; $i++) { 
			if ($this->rules[$i]["name"]==$name)
				return $i;
		}
		return false;
	}
}
/*! Wrapper for collection of sorting rules
**/
class SortInterface extends EventInterface{
	/*! constructor
		creates a new interface based on existing request
		@param request 
			DataRequestConfig object
	*/
	public function __construct($request){
		parent::__construct($request);
		$this->rules = &$request->get_sort_by_ref();
	}
	/*! add new sorting rule
		
		@param name 
			name of field
		@param dir
			direction of sorting
	*/
	public function add($name,$dir){
		$this->request->set_sort($name,$dir);
	}
	public function store(){
		$this->request->set_sort_by($this->rules);
	}
}
/*! Wrapper for collection of filtering rules
**/
class FilterInterface extends EventInterface{
	/*! constructor
		creates a new interface based on existing request
		@param request 
			DataRequestConfig object
	*/	
	public function __construct($request){
		$this->request = $request;
		$this->rules = &$request->get_filters_ref();
	}
	/*! add new filatering rule
		
		@param name 
			name of field
		@param value
			value to filter by
		@param rule
			filtering rule
	*/
	public function add($name,$value,$rule){
		$this->request->set_filter($name,$value,$rule);
	}
	public function store(){
		$this->request->set_filters($this->rules);
	}
}

/*! base class for component item representation	
**/
class DataItem{
	protected $data; //!< hash of data
	protected $config;//!< DataConfig instance
	protected $index;//!< index of element
	protected $skip;//!< flag , which set if element need to be skiped during rendering
	/*! constructor
		
		@param data
			hash of data
		@param config
			DataConfig object
		@param index
			index of element
	*/
	function __construct($data,$config,$index){
		$this->config=$config;
		$this->data=$data;
		$this->index=$index;
		$this->skip=false;
	}
	/*! get named value
		
		@param name 
			name or alias of field
		@return 
			value from field with provided name or alias
	*/
	public function get_value($name){
		return $this->data[$name];
	}
	/*! set named value
		
		@param name 
			name or alias of field
		@param value
			value for field with provided name or alias
	*/
	public function set_value($name,$value){
		return $this->data[$name]=$value;
	}
	/*! get id of element
		@return 
			id of element
	*/
	public function get_id(){
		$id = $this->config->id["name"];
		if (array_key_exists($id,$this->data))
			return $this->data[$id];
		return false;
	}
	/*! change id of element
		
		@param value 
			new id value
	*/
	public function set_id($value){
		$this->data[$this->config->id["name"]]=$value;
	}
	/*! get index of element
		
		@return 
			index of element
	*/
	public function get_index(){
		return $this->index;
	}
	/*! mark element for skiping ( such element will not be rendered )
	*/
	public function skip(){
		$this->skip=true;
	}
	
	/*! return self as XML string
	*/
	public function to_xml(){
		return $this->to_xml_start().$this->to_xml_end();
	}
	
	/*! replace xml unsafe characters
		
		@param string 
			string to be escaped
		@return 
			escaped string
	*/
	protected function xmlentities($string) { 
   		return str_replace( array( '&', '"', "'", '<', '>', '’' ), array( '&amp;' , '&quot;', '&apos;' , '&lt;' , '&gt;', '&apos;' ), $string);
	}
	
	/*! return starting tag for self as XML string 
	*/
	public function to_xml_start(){
		$str="<item";
		for ($i=0; $i < sizeof($this->config->data); $i++){ 
			$name=$this->config->data[$i]["name"];
			$str.=" ".$name."='".$this->xmlentities($this->data[$name])."'";
		}
		return $str.">";
	}
	/*! return ending tag for XML string
	*/
	public function to_xml_end(){
		return "</item>";
	}
}





/*! Base connector class
	This class used as a base for all component specific connectors. 
	Can be used on its own to provide raw data.	
**/
class Connector {
	protected $config;//DataConfig instance
	protected $request;//DataRequestConfig instance
	protected $names;//!< hash of names for used classes
	private $encoding="utf-8";//!< assigned encoding (UTF-8 by default) 
	private $editing=false;//!< flag of edit mode ( response for dataprocessor )
	private $updating=false;//!< flag of update mode ( response for data-update )
	private $db; //!< db connection resource
	protected $dload;//!< flag of dyn. loading mode
	public $access;  //!< AccessMaster instance
	
	public $sql;	//DataWrapper instance
	public $event;	//EventMaster instance
	public $limit=false;
	
	private $id_seed=0; //!< default value, used to generate auto-IDs
	protected $live_update = false; // actions table name for autoupdating
	
	/*! constructor
		
		Here initilization of all Masters occurs, execution timer initialized
		@param db 
			db connection resource
		@param type
			string , which hold type of database ( MySQL or Postgre ), optional, instead of short DB name, full name of DataWrapper-based class can be provided
		@param item_type
			name of class, which will be used for item rendering, optional, DataItem will be used by default
		@param data_type
			name of class which will be used for dataprocessor calls handling, optional, DataProcessor class will be used by default. 
	*/	
	public function __construct($db,$type=false, $item_type=false, $data_type=false){
		$this->exec_time=microtime(true);

		if (!$type) $type="MySQL";
		if (class_exists($type."DBDataWrapper",false)) $type.="DBDataWrapper";
		if (!$item_type) $item_type="DataItem";
		if (!$data_type) $data_type="DataProcessor";
		
		$this->names=array(
			"db_class"=>$type,
			"item_class"=>$item_type,
			"data_class"=>$data_type,
		);
		
		$this->config = new DataConfig();
		$this->request = new DataRequestConfig();
		$this->event = new EventMaster();
		$this->access = new AccessMaster();

		if (!class_exists($this->names["db_class"],false))
			throw new Exception("DB class not found: ".$this->names["db_class"]);
		$this->sql = new $this->names["db_class"]($db,$this->config);
		
		$this->db=$db;//saved for options connectors, if any
		
		EventMaster::trigger_static("connectorCreate",$this);
	}

	/*! return db connection resource
		nested class may neeed to access live connection object
		@return 
			DB connection resource
	*/
	protected function get_connection(){
		return $this->db;
	}

	public function get_config(){
		return new DataConfig($this->config);
	}
	
	public function get_request(){
		return new DataRequestConfig($this->config);
	}


	/*! config connector based on table
		
		@param table 
			name of table in DB
		@param id 
			name of id field
		@param fields
			list of fields names
		@param extra
			list of extra fields, optional, such fields will not be included in data rendering, but will be accessible in all inner events
		@param relation_id
			name of field used to define relations for hierarchical data organization, optional
	*/
	public function render_table($table,$id="",$fields=false,$extra=false,$relation_id=false){
		$this->configure($table,$id,$fields,$extra,$relation_id);
		return $this->render();
	}
	public function configure($table,$id="",$fields=false,$extra=false,$relation_id=false){
        if ($fields === false){
            //auto-config
            $info = $this->sql->fields_list($table);
            $fields = implode(",",$info["fields"]);
            if ($info["key"])
                $id = $info["key"];
        }
		$this->config->init($id,$fields,$extra,$relation_id);
		$this->request->set_source($table);
	}
	
	protected function uuid(){
		return time()."x".$this->id_seed++;
	}
	
	/*! config connector based on sql
		
		@param sql 
			sql query used as base of configuration
		@param id 
			name of id field
		@param fields
			list of fields names
		@param extra
			list of extra fields, optional, such fields will not be included in data rendering, but will be accessible in all inner events
		@param relation_id
			name of field used to define relations for hierarchical data organization, optional
	*/
	public function render_sql($sql,$id,$fields,$extra=false,$relation_id=false){
		$this->config->init($id,$fields,$extra,$relation_id);
		$this->request->parse_sql($sql);
		return $this->render();
	}
	
	/*! render already configured connector
		
		@param config
			configuration of data
		@param request
			configuraton of request
	*/
	public function render_connector($config,$request){
		$this->config->copy($config);
		$this->request->copy($request);
		return $this->render();
	}	
	
	/*! render self
		process commands, output requested data as XML
	*/	
	public function render(){
		EventMaster::trigger_static("connectorInit",$this);
		
		$this->parse_request();
		if ($this->live_update !== false && $this->updating!==false) {
			$this->live_update->get_updates();
		} else {
			if ($this->editing){
				$dp = new $this->names["data_class"]($this,$this->config,$this->request);
				$dp->process($this->config,$this->request);
			}
			else {
				$wrap = new SortInterface($this->request);
				$this->event->trigger("beforeSort",$wrap);
				$wrap->store();
				
				$wrap = new FilterInterface($this->request);
				$this->event->trigger("beforeFilter",$wrap);
				$wrap->store();
		
				$this->output_as_xml( $this->sql->select($this->request) );
			}
		}
		$this->end_run();
	}
	
	/*! prevent SQL injection through column names
		replace dangerous chars in field names
		@param str 
			incoming field name
		@return 
			safe field name
	*/
	protected function safe_field_name($str){
		return strtok($str, " \n\t;',");
	}
	
	/*! limit max count of records
		connector will ignore any records after outputing max count
		@param limit 
			max count of records
		@return 
			none
	*/
	public function set_limit($limit){
		$this->limit = $limit;
	}
	
	protected function parse_request_mode(){
		//detect edit mode
        if (isset($_GET["editing"])){
			$this->editing=true;
        } else if (isset($_POST["ids"])){
			$this->editing=true;
			LogMaster::log('While there is no edit mode mark, POST parameters similar to edit mode detected. \n Switching to edit mode ( to disable behavior remove POST[ids]');
		} else if (isset($_GET['dhx_version'])){
			$this->updating = true;
        }
	}
	
	/*! parse incoming request, detects commands and modes
	*/
	protected function parse_request(){
		//set default dyn. loading params, can be reset in child classes
		if ($this->dload)
			$this->request->set_limit(0,$this->dload);
		else if ($this->limit)
			$this->request->set_limit(0,$this->limit);
		
		$this->parse_request_mode();

        if ($this->live_update && ($this->updating || $this->editing)){
            $this->request->set_version($_GET["dhx_version"]);
            $this->request->set_user($_GET["dhx_user"]);
        }
		
		if (isset($_GET["dhx_sort"]))
			foreach($_GET["dhx_sort"] as $k => $v){
				$k = $this->safe_field_name($k);
				$this->request->set_sort($this->resolve_parameter($k),$v);
			}
				
		if (isset($_GET["dhx_filter"]))
			foreach($_GET["dhx_filter"] as $k => $v){
				$k = $this->safe_field_name($k);
				$this->request->set_filter($this->resolve_parameter($k),$v);
			}
			
		
	}

	/*! convert incoming request name to the actual DB name
		@param name 
			incoming parameter name
		@return 
			name of related DB field
	*/
	protected function resolve_parameter($name){
		return $name;
	}


	/*! replace xml unsafe characters

		@param string
			string to be escaped
		@return
			escaped string
	*/
	private function xmlentities($string) {
   		return str_replace( array( '&', '"', "'", '<', '>', '’' ), array( '&amp;' , '&quot;', '&apos;' , '&lt;' , '&gt;', '&apos;' ), $string);
	}
    
	/*! render from DB resultset
		@param res
			DB resultset 
		process commands, output requested data as XML
	*/
	protected function render_set($res){
		$output="";
		$index=0;
		$this->event->trigger("beforeRenderSet",$this,$res,$this->config);
		while ($data=$this->sql->get_next($res)){
			$data = new $this->names["item_class"]($data,$this->config,$index);
			if ($data->get_id()===false)
				$data->set_id($this->uuid());
			$this->event->trigger("beforeRender",$data);
			$output.=$data->to_xml();
			$index++;
		}
		return $output;
	}
	
	/*! output fetched data as XML
		@param res
			DB resultset 
	*/
	protected function output_as_xml($res){
		$start="<?xml version='1.0' encoding='".$this->encoding."' ?>".$this->xml_start();
		$end=$this->render_set($res).$this->xml_end();
		
		$out = new OutputWriter($start, $end);
		$this->event->trigger("beforeOutput", $this, $out);
		
		$out->output();
	}


	/*! end processing
		stop execution timer, kill the process
	*/
	protected function end_run(){
		$time=microtime(true)-$this->exec_time;
		LogMaster::log("Done in {$time}s");
		flush();
		die();
	}
	
	/*! set xml encoding
		
		methods sets only attribute in XML, no real encoding conversion occurs	
		@param encoding 
			value which will be used as XML encoding
	*/
	public function set_encoding($encoding){
		$this->encoding=$encoding;
	}

	/*! enable or disable dynamic loading mode
		
		@param count 
			count of rows loaded from server, actual only for grid-connector, can be skiped in other cases. 
			If value is a false or 0 - dyn. loading will be disabled
	*/
	public function dynamic_loading($count){
		$this->dload=$count;
	}	
		
	/*! enable logging
		
		@param path 
			path to the log file. If set as false or empty strig - logging will be disabled
		@param client_log
			enable output of log data to the client side
	*/
	public function enable_log($path=true,$client_log=false){
		LogMaster::enable_log($path,$client_log);
	}
	
	/*! provides infor about current processing mode
		@return 
			true if processing dataprocessor command, false otherwise
	*/
	public function is_select_mode(){
		$this->parse_request_mode();
		return !$this->editing;
	}
	
	public function is_first_call(){
		$this->parse_request_mode();
		return !($this->editing || $this->updating || $this->request->get_start() || sizeof($this->request->get_filters()) || sizeof($this->request->get_sort_by()));
		
	}
	
	/*! renders self as  xml, starting part
	*/
	protected function xml_start(){
		return "<data>";
	}
	/*! renders self as  xml, ending part
	*/
	protected function xml_end(){
		return "</data>";
	}


	public function insert($data) {
		$action = new DataAction('inserted', false, $data);
		$request = new DataRequestConfig();
		$request->set_source($this->request->get_source());
		
		$this->config->limit_fields($data);
		$this->sql->insert($action,$request);
		$this->config->restore_fields($data);
		
		return $action->get_new_id();
	}
	
	public function delete($id) {
		$action = new DataAction('deleted', $id, array());
		$request = new DataRequestConfig();
		$request->set_source($this->request->get_source());
		
		$this->sql->delete($action,$request);
		return $action->get_status();
}

	public function update($data) {
		$action = new DataAction('updated', $data[$this->config->id["name"]], $data);
		$request = new DataRequestConfig();
		$request->set_source($this->request->get_source());

		$this->config->limit_fields($data);
		$this->sql->update($action,$request);
		$this->config->restore_fields($data);
		
		return $action->get_status();
	}

	/*! sets actions_table for Optimistic concurrency control mode and start it
		@param table_name
			name of database table which will used for saving actions
		@param url
			url used for update notifications
	*/	
	public function enable_live_update($table, $url=false){
		$this->live_update = new DataUpdate($this->sql, $this->config, $this->request, $table,$url);
        $this->live_update->set_event($this->event,$this->names["item_class"]);
		$this->event->attach("beforeOutput", 		Array($this->live_update, "version_output"));
		$this->event->attach("beforeFiltering", 	Array($this->live_update, "get_updates"));
		$this->event->attach("beforeProcessing", 	Array($this->live_update, "check_collision"));
		$this->event->attach("afterProcessing", 	Array($this->live_update, "log_operations"));
	}
}


/*! wrapper around options collection, used for comboboxes and filters
**/
class OptionsConnector extends Connector{
	protected $init_flag=false;//!< used to prevent rendering while initialization
	public function __construct($res,$type=false,$item_type=false,$data_type=false){
		if (!$item_type) $item_type="DataItem";
		if (!$data_type) $data_type=""; //has not sense, options not editable
		parent::__construct($res,$type,$item_type,$data_type);
	}
	/*! render self
		process commands, return data as XML, not output data to stdout, ignore parameters in incoming request
		@return
			data as XML string
	*/	
	public function render(){
		if (!$this->init_flag){
			$this->init_flag=true;
			return "";
		}
		$res = $this->sql->select($this->request);
		return $this->render_set($res);
	}
}



class DistinctOptionsConnector extends OptionsConnector{
	/*! render self
		process commands, return data as XML, not output data to stdout, ignore parameters in incoming request
		@return
			data as XML string
	*/	
	public function render(){
		if (!$this->init_flag){
			$this->init_flag=true;
			return "";
		}
		$res = $this->sql->get_variants($this->config->text[0]["db_name"],$this->request);
		return $this->render_set($res);
	}
}

?>
