<?php
require_once("base_connector.php");

/*! DataItem class for Tree component
**/

class TreeDataItem extends DataItem{
	private $im0;//!< image of closed folder
	private $im1;//!< image of opened folder
	private $im2;//!< image of leaf item
	private $check;//!< checked state
	private $kids=-1;//!< checked state
	private $attrs;//!< collection of custom attributes
	
	function __construct($data,$config,$index){
		parent::__construct($data,$config,$index);
		
		$this->im0=false;
		$this->im1=false;
		$this->im2=false;
		$this->check=false;
		$this->attrs = array();
		$this->userdata = array();
	}
	/*! get id of parent record
		
		@return 
			id of parent record
	*/
	function get_parent_id(){
		return $this->data[$this->config->relation_id["name"]];
	}
	/*! get state of items checkbox
		
		@return 
			state of item's checkbox as int value, false if state was not defined
	*/
	function get_check_state(){
		return $this->check;
	}
	/*! set state of item's checkbox

		@param value 
			int value, 1 - checked, 0 - unchecked, -1 - third state
	*/
	function set_check_state($value){
		$this->check=$value;
	}
	
	/*! return count of child items
		-1 if there is no info about childs
		@return 
			count of child items
	*/
	function has_kids(){
		return $this->kids;
	}
	/*! sets count of child items
		@param value
			count of child items
	*/
	function set_kids($value){
		$this->kids=$value;
	}
	
	/*! set custom attribute 
		
		@param name 
			name of the attribute
		@param value
			new value of the attribute
	*/
	function set_attribute($name, $value){
		switch($name){
			case "id": 
				$this->set_id($value);
				break;
			case "text": 
				$this->data[$this->config->text[0]["name"]]=$value;
				break;
			case "checked": 
				$this->set_check_state($value);
				break;
			case "im0": 
				$this->im0=$value;
				break;
			case "im1": 
				$this->im1=$value;
				break;
			case "im2": 
				$this->im2=$value;
				break;
			case "child": 
				$this->set_kids($value);
				break;
			default:
				$this->attrs[$name]=$value;
		}
	}
	
	/*! set userdata section for the item
		
		@param name
			name of userdata
		@param value
			value of userdata
	*/
	function set_userdata($name, $value){
		$this->userdata[$name]=$value;
	}
	
	/*! assign image for tree's item
		
		@param img_folder_closed 
			image for item, which represents folder in closed state
		@param img_folder_open 
			image for item, which represents folder in opened state, optional
		@param img_leaf 
			image for item, which represents leaf item, optional
	*/
	function set_image($img_folder_closed,$img_folder_open=false,$img_leaf=false){
		$this->im0=$img_folder_closed;
		$this->im1=$img_folder_open?$img_folder_open:$img_folder_closed;
		$this->im2=$img_leaf?$img_leaf:$img_folder_closed;
	}
	/*! return self as XML string, starting part
	*/
	function to_xml_start(){
		if ($this->skip) return "";
		
		$str1="<item id='".$this->get_id()."' text='".$this->xmlentities($this->data[$this->config->text[0]["name"]])."' ";
		if ($this->has_kids()==true) $str1.="child='".$this->has_kids()."' ";
		if ($this->im0) $str1.="im0='".$this->im0."' ";
		if ($this->im1) $str1.="im1='".$this->im0."' ";
		if ($this->im2) $str1.="im2='".$this->im0."' ";
		if ($this->check) $str1.="checked='".$this->check."' ";
		foreach ($this->attrs as $key => $value)
			$str1.=$key."='".$this->xmlentities($value)."' ";
		$str1.=">";
		foreach ($this->userdata as $key => $value)
			$str1.="<userdata name='".$key."'><![CDATA[".$value."]]></userdata>";
			
		return $str1;
	}
	/*! return self as XML string, ending part
	*/
	function to_xml_end(){
		if ($this->skip) return "";
		return "</item>";
	}

}

require_once("filesystem_item.php");

/*! Connector for the dhtmlxtree
**/
class TreeConnector extends Connector{
	private $id_swap = array();
	
	/*! constructor
		
		Here initilization of all Masters occurs, execution timer initialized
		@param res 
			db connection resource
		@param type
			string , which hold type of database ( MySQL or Postgre ), optional, instead of short DB name, full name of DataWrapper-based class can be provided
		@param item_type
			name of class, which will be used for item rendering, optional, DataItem will be used by default
		@param data_type
			name of class which will be used for dataprocessor calls handling, optional, DataProcessor class will be used by default. 
	*/	
	public function __construct($res,$type=false,$item_type=false,$data_type=false){
		if (!$item_type) $item_type="TreeDataItem";
		if (!$data_type) $data_type="TreeDataProcessor";
		parent::__construct($res,$type,$item_type,$data_type);
		
		$this->event->attach("afterInsert",array($this,"parent_id_correction_a"));
		$this->event->attach("beforeProcessing",array($this,"parent_id_correction_b"));
	}
	
	/*! store info about ID changes during insert operation
		@param dataAction 
			data action object during insert operation
	*/
	public function parent_id_correction_a($dataAction){
		$this->id_swap[$dataAction->get_id()]=$dataAction->get_new_id();
	}
	/*! update ID if it was affected by previous operation
		@param dataAction 
			data action object, before any processing operation
	*/
	public function parent_id_correction_b($dataAction){
		$relation = $this->config->relation_id["db_name"];
		$value = $dataAction->get_value($relation);
		
		if (array_key_exists($value,$this->id_swap))
			$dataAction->set_value($relation,$this->id_swap[$value]);
	}
	
	
	public function parse_request(){
		parent::parse_request();
		
		if (isset($_GET["id"]))
			$this->request->set_relation($_GET["id"]);
		else
			$this->request->set_relation("0");
			
		$this->request->set_limit(0,0); //netralize default reaction on dyn. loading mode
	}
	

   
	protected function render_set($res){
		$output="";
		$index=0;
		while ($data=$this->sql->get_next($res)){
			$data = new $this->names["item_class"]($data,$this->config,$index);
			$this->event->trigger("beforeRender",$data);
		//there is no info about child elements, 
		//if we are using dyn. loading - assume that it has,
		//in normal mode juse exec sub-render routine			
			if ($data->has_kids()===-1 && $this->dload)
					$data->set_kids(true);
			$output.=$data->to_xml_start();
			if ($data->has_kids()===-1 || ( $data->has_kids()==true && !$this->dload)){
				$sub_request = new DataRequestConfig($this->request);
				$sub_request->set_relation($data->get_id());
				$output.=$this->render_set($this->sql->select($sub_request));
			}
			$output.=$data->to_xml_end();
			$index++;
		}
		return $output;
	}
   /*! renders self as  xml, starting part
	*/
	public function xml_start(){
		return "<tree id='".$this->request->get_relation()."'>";
	}
	
	/*! renders self as  xml, ending part
	*/
	public function xml_end(){
		return "</tree>";
	}
}


class TreeDataProcessor extends DataProcessor{
	
	function __construct($connector,$config,$request){
		parent::__construct($connector,$config,$request);
		$request->set_relation(false);
	}
		
	/*! convert incoming data name to valid db name
		converts c0..cN to valid field names
		@param data 
			data name from incoming request
		@return 
			related db_name
	*/
	function name_data($data){
		if ($data=="tr_pid")
			return $this->config->relation_id["db_name"];
		if ($data=="tr_text")
			return $this->config->text[0]["db_name"];
		return $data;
	}
}		

?>