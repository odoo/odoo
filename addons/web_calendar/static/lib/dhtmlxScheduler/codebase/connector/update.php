<?php

/*! DataItemUpdate class for realization Optimistic concurrency control
	Wrapper for DataItem object
	It's used during outputing updates instead of DataItem object
	Create wrapper for every data item with update information.
*/
class DataItemUpdate extends DataItem {


	/*! constructor
		@param data
			hash of data
		@param config
			DataConfig object
		@param index
			index of element
	*/
	public function __construct($data,$config,$index,$type){
		$this->config=$config;
		$this->data=$data;
		$this->index=$index;
		$this->skip=false;
		$this->child = new $type($data, $config, $index);
	}

	/*! returns parent_id (for Tree and TreeGrid components)
	*/
	public function get_parent_id(){
		if (method_exists($this->child, 'get_parent_id')) {
			return $this->child->get_parent_id();
		} else {
			return '';
		}
	}


	/*! generate XML on the data hash base
	*/
	public function to_xml(){
        $str= "<update ";
		$str .= 'status="'.$this->data['type'].'" ';
		$str .= 'id="'.$this->data['dataId'].'" ';
		$str .= 'parent="'.$this->get_parent_id().'"';
		$str .= '>';
		$str .= $this->child->to_xml();
		$str .= '</update>';
        return $str;
	}

	/*! return starting tag for XML string
	*/
	public function to_xml_start(){
		$str="<update ";
		$str .= 'status="'.$this->data['type'].'" ';
		$str .= 'id="'.$this->data['dataId'].'" ';
		$str .= 'parent="'.$this->get_parent_id().'"';
		$str .= '>';
		$str .= $this->child->to_xml_start();
		return $str;
	}

	/*! return ending tag for XML string
	*/
	public function to_xml_end(){
		$str = $this->child->to_xml_end();
		$str .= '</update>';
		return $str;
	}

	/*! returns false for outputing only current item without child items
	*/
	public function has_kids(){
		return false;
	}

	/*! sets count of child items
		@param value
			count of child items
	*/
	public function set_kids($value){
		if (method_exists($this->child, 'set_kids')) {
			$this->child->set_kids($value);
		}
	}

	/*! sets attribute for item
	*/
	public function set_attribute($name, $value){
		if (method_exists($this->child, 'set_attribute')) {
			LogMaster::log("setting attribute: \nname = {$name}\nvalue = {$value}");
			$this->child->set_attribute($name, $value);
		} else {
			LogMaster::log("set_attribute method doesn't exists");
		}
	}
}


class DataUpdate{
	
	protected $table; //!< table , where actions are stored
	protected $url; //!< url for notification service, optional
    protected $sql; //!< DB wrapper object
    protected $config; //!< DBConfig object
    protected $request; //!< DBRequestConfig object
    protected $event;
    protected $item_class;
    protected $demu;
	
	//protected $config;//!< DataConfig instance
	//protected $request;//!< DataRequestConfig instance
	
	/*! constructor
	  
	  @param connector 
	     Connector object
	  @param config
	     DataConfig object
	  @param request
	     DataRequestConfig object
	*/
	function __construct($sql, $config, $request, $table, $url){
        $this->config= $config;
        $this->request= $request;
        $this->sql = $sql;
        $this->table=$table;
        $this->url=$url;
        $this->demu = false;
	}

    public function set_demultiplexor($path){
        $this->demu = $path;
    }

    public function set_event($master, $name){
        $this->event = $master;
        $this->item_class = $name;
    }
   	
	private function select_update($actions_table, $join_table, $id_field_name, $version, $user) {
		$sql = "SELECT * FROM  {$actions_table}";
		$sql .= " LEFT OUTER JOIN {$join_table} ON ";
		$sql .= "{$actions_table}.DATAID = {$join_table}.{$id_field_name} ";
		$sql .= "WHERE {$actions_table}.ID > '{$version}' AND {$actions_table}.USER <> '{$user}'";
		return $sql;
	}

	private function get_update_max_version() {
		$sql = "SELECT MAX(id) as VERSION FROM {$this->table}";
		$res = $this->sql->query($sql);
		$data = $this->sql->get_next($res);
		
		if ($data == false || $data['VERSION'] == false) 
			return 1;
		else
			return $data['VERSION'];
	}

	private function log_update_action($actions_table, $dataId, $status, $user) {
		$sql = "INSERT INTO {$actions_table} (DATAID, TYPE, USER) VALUES ('{$dataId}', '{$status}', '{$user}')";
		$this->sql->query($sql);
        if ($this->demu)
            file_get_contents($this->demu);
	}




	/*! records operations in actions_table
		@param action
			DataAction object
	*/
	public function log_operations($action) {
		$type = 	$this->sql->escape($action->get_status());
		$dataId = 	$this->sql->escape($action->get_new_id());
		$user = 	$this->sql->escape($this->request->get_user());
		if ($type!="error" && $type!="invalid" && $type !="collision") {
			$this->log_update_action($this->table, $dataId, $type, $user);
		}
	}


	/*! return action version in XMl format
	*/
	public function get_version() {
		$version = $this->get_update_max_version();
		return "<userdata name='version'>".$version."</userdata>";
	}


	/*! adds action version in output XML as userdata
	*/
	public function version_output() {
			echo $this->get_version();
	}


	/*! create update actions in XML-format and sends it to output
	*/
	public function get_updates() {
		$sub_request = new DataRequestConfig($this->request);
		$version =	$this->request->get_version();
		$user = 	$this->request->get_user();

		$sub_request->parse_sql($this->select_update($this->table, $this->request->get_source(), $this->config->id['db_name'], $version, $user));
		$sub_request->set_relation(false);

		$output = $this->render_set($this->sql->select($sub_request), $this->item_class);
        
		ob_clean();
		header("Content-type:text/xml");
        
		echo $this->updates_start();
		echo $this->get_version();
		echo $output;
		echo $this->updates_end();
	}

    
	protected function render_set($res, $name){
		$output="";
		$index=0;
		while ($data=$this->sql->get_next($res)){
			$data = new DataItemUpdate($data,$this->config,$index, $name);
			$this->event->trigger("beforeRender",$data);
			$output.=$data->to_xml();
			$index++;
		}
		return $output;
	}

	/*! returns update start string
	*/
	protected function updates_start() {
		$start = '<updates>';
		return $start;
	}

	/*! returns update end string
	*/
	protected function updates_end() {
		$start = '</updates>';
		return $start;
	}

	/*! checks if action version given by client is deprecated
		@param action
			DataAction object
	*/
	public function check_collision($action) {
		$version =	$this->sql->escape($this->request->get_version());
		//$user = 	$this->sql->escape($this->request->get_user());
		$last_version = $this->get_update_max_version();
		if (($last_version > $version)&&($action->get_status() == 'update')) {
			$action->error();
			$action->set_status('collision');
		}
	}
}
	
?>