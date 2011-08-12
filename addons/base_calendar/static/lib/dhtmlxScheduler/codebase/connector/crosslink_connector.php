<?php

class DelayedConnector extends Connector{
	protected $init_flag=false;//!< used to prevent rendering while initialization
	private $data_mode=false;//!< flag to separate xml and data request modes
	private $data_result=false;//<! store results of query
	
	public function dataMode($name){
		$this->data_mode = $name;
		$this->data_result=array();
	}
	public function getDataResult(){
		return $this->data_result;
	}
	
	public function render(){
		if (!$this->init_flag){
			$this->init_flag=true;
			return "";
		}
		return parent::render();
	}
	
	protected function output_as_xml($res){
		if ($this->data_mode){
			while ($data=$this->sql->get_next($res)){
				$this->data_result[]=$data[$this->data_mode];
			}
		}
		else 
			return parent::output_as_xml($res);
	}
	protected function end_run(){
		if (!$this->data_mode)
			parent::end_run();
	}
}
	
class CrossOptionsConnector extends Connector{
	public $options, $link;
	private $master_name, $link_name, $master_value;
	
	public function __construct($res,$type=false,$item_type=false,$data_type=false){
		$this->options = new OptionsConnector($res,$type,$item_type,$data_type);
		$this->link = new DelayedConnector($res,$type,$item_type,$data_type);
		
		EventMaster::attach_static("connectorInit",array($this, "handle"));
	}
	public function handle($conn){
		if ($conn instanceof DelayedConnector) return;
		if ($conn instanceof OptionsConnector) return;
		
		$this->master_name = $this->link->get_config()->id["db_name"];
		$this->link_name = $this->options->get_config()->id["db_name"];
	
		$this->link->event->attach("beforeFilter",array($this, "get_only_related"));
		
		if (isset($_GET["dhx_crosslink_".$this->link_name])){
			$this->get_links($_GET["dhx_crosslink_".$this->link_name]);
			die();
		}
		
		if (!$this->dload){
			$conn->event->attach("beforeRender", array($this, "getOptions"));
			$conn->event->attach("beforeRenderSet", array($this, "prepareConfig"));
		}
		
		
		$conn->event->attach("afterProcessing", array($this, "afterProcessing"));
	}
	public function prepareConfig($conn, $res, $config){
		$config->add_field($this->link_name);
	}
	public function getOptions($data){
		$this->link->dataMode($this->link_name);

		$this->get_links($data->get_value($this->master_name));
		
		$data->set_value($this->link_name, implode(",",$this->link->getDataResult()));
	}
	public function get_links($id){
		$this->master_value = $id;
		$this->link->render();
	}
	public function get_only_related($filters){
		$index = $filters->index($this->master_name);
		if ($index!==false){
			$filters->rules[$index]["value"]=$this->master_value;
		} else
			$filters->add($this->master_name, $this->master_value, "=");
	}
	public function afterProcessing($action){
		$status = $action->get_status();
		
		$master_key = $action->get_value($this->master_name);	
		$link_key = $action->get_value($this->link_name);
		$link_key = explode(',', $link_key);
		
		if ($status == "inserted")
			$master_key = $action->get_new_id();
			
		switch ($status){
			case "deleted":
				$this->link->delete($master_key);
				break;
			case "updated":
				$this->link->delete($master_key);
			case "inserted":
				for ($i=0; $i < sizeof($link_key); $i++)
					if ($link_key[$i]!="")
						$this->link->insert(array(
							$this->link_name => $link_key[$i],
							$this->master_name => $master_key
						));
				break;
		}
	}
}

?>