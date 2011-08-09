<?php
require_once("grid_connector.php");

/*! DataItem class for TreeGrid component
**/
class TreeGridDataItem extends GridDataItem{
	private $kids=-1;//!< checked state
	
	function __construct($data,$config,$index){
		parent::__construct($data,$config,$index);
		$this->im0=false;
	}
	/*! return id of parent record

		@return 
			id of parent record
	*/
	function get_parent_id(){
		return $this->data[$this->config->relation_id["name"]];
	}
	/*! assign image to treegrid's item
		longer description
		@param img 
			relative path to the image
	*/
	function set_image($img){
		$this->set_cell_attribute($this->config->text[0]["name"],"image",$img);
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
		if ($value) 
			$this->set_row_attribute("xmlkids",$value);
	}
}
/*! Connector for dhtmlxTreeGrid
**/
class TreeGridConnector extends GridConnector{
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
		if (!$item_type) $item_type="TreeGridDataItem";
		if (!$data_type) $data_type="TreeGridDataProcessor";
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
		
	/*! process treegrid specific options in incoming request
	*/
	public function parse_request(){
		parent::parse_request();
		
		if (isset($_GET["id"]))
			$this->request->set_relation($_GET["id"]);
		else
			$this->request->set_relation("0");
			
		$this->request->set_limit(0,0); //netralize default reaction on dyn. loading mode
	}
	
	/*! process treegrid specific options in incoming request
	*/	
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
	protected function xml_start(){
		return "<rows parent='".$this->request->get_relation()."'>";
	}	
}

/*! DataProcessor class for Grid component
**/
class TreeGridDataProcessor extends GridDataProcessor{
	
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
		
		if ($data=="gr_pid")
			return $this->config->relation_id["name"];
		else return parent::name_data($data);
	}
}
?>