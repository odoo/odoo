/**
 * CFPrint打印辅助类
 * ver 1.3
 * 康虎软件工作室
 * Email: wdmsyf@sina.com
 * QQ: 360026606
 * 微信: 360026606
 *
 * 一、用法：
 * 启动康虎云打印服务器后，在应用系统中，通过服务端代码，生成打印所需要的报表数据Json字符，并命名为_reportData，即可自动打印。
 * 通过重设 _delay_send 和 _delay_close 两个参数，可以调整发送打印以及打印完毕后关闭报表页面的延时时长。
 *
 *  其中：_reportData 可以是json对象，也可以是json字符串
 *
 * 二、连接状态
 * cfprint.CONNECTING: 正在连接
 * cfprint.OPEN: 已连接
 * cfprint.CLOSING: 连接正在关闭
 * cfprint.CLOSED: 连接已关闭
 *
 * 检测当前连接状态：
 * if ( cfprint.state() === cfprint.OPEN)  {...}
 */

/* 
//示例数据：
var _reportData = '{"template":"waybill_huaxia3.fr3","Cols":[{"type":"str","size":255,"name":"HAWB#","required":false},{"type":"int","size":0,"name":"NO","required":false},{"type":"float","size":0,"name":"华夏单号","required":false},{"type":"integer","size":0,"name":"鹭路通单号","required":false},{"type":"str","size":255,"name":"发件人","required":false},{"type":"str","size":255,"name":"发件人地址","required":false},{"type":"str","size":255,"name":"发件人电话","required":false},{"type":"str","size":255,"name":"发货国家","required":false},{"type":"str","size":255,"name":"收件人","required":false},{"type":"str","size":255,"name":"收件人地址","required":false},{"type":"str","size":255,"name":"收件人电话","required":false},{"type":"str","size":255,"name":"收货人证件号码","required":false},{"type":"str","size":255,"name":"收货省份","required":false},{"type":"float","size":0,"name":"总计费重量","required":false},{"type":"int","size":0,"name":"总件数","required":false},{"type":"float","size":0,"name":"申报总价（CNY）","required":false},{"type":"float","size":0,"name":"申报总价（JPY）","required":false},{"type":"int","size":0,"name":"件数1","required":false},{"type":"str","size":255,"name":"品名1","required":false},{"type":"float","size":0,"name":"单价1（JPY）","required":false},{"type":"str","size":255,"name":"单位1","required":false},{"type":"float","size":0,"name":"申报总价1（CNY）","required":false},{"type":"float","size":0,"name":"申报总价1（JPY）","required":false},{"type":"int","size":0,"name":"件数2","required":false},{"type":"str","size":255,"name":"品名2","required":false},{"type":"float","size":0,"name":"单价2（JPY）","required":false},{"type":"str","size":255,"name":"单位2","required":false},{"type":"float","size":0,"name":"申报总价2（CNY）","required":false},{"type":"float","size":0,"name":"申报总价2（JPY）","required":false},{"type":"int","size":0,"name":"件数3","required":false},{"type":"str","size":255,"name":"品名3","required":false},{"type":"float","size":0,"name":"单价3（JPY）","required":false},{"type":"str","size":255,"name":"单位3","required":false},{"type":"float","size":0,"name":"申报总价3（CNY）","required":false},{"type":"float","size":0,"name":"申报总价3（JPY）","required":false},{"type":"int","size":0,"name":"件数4","required":false},{"type":"str","size":255,"name":"品名4","required":false},{"type":"float","size":0,"name":"单价4（JPY）","required":false},{"type":"str","size":255,"name":"单位4","required":false},{"type":"float","size":0,"name":"申报总价4（CNY）","required":false},{"type":"float","size":0,"name":"申报总价4（JPY）","required":false},{"type":"int","size":0,"name":"件数5","required":false},{"type":"str","size":255,"name":"品名5","required":false},{"type":"float","size":0,"name":"单价5（JPY）","required":false},{"type":"str","size":255,"name":"单位5","required":false},{"type":"float","size":0,"name":"申报总价5（CNY）","required":false},{"type":"float","size":0,"name":"申报总价5（JPY）","required":false},{"type":"str","size":255,"name":"参考号","required":false},{"type":"AutoInc","size":0,"name":"ID","required":false}],"Data":[{"鹭路通单号":730293,"发货国家":"日本","单价1（JPY）":null,"申报总价2（JPY）":null,"单价4（JPY）":null,"申报总价2（CNY）":null,"申报总价5（JPY）":null,"华夏单号":200303900791,"申报总价5（CNY）":null,"收货人证件号码":null,"申报总价1（JPY）":null,"单价3（JPY）":null,"申报总价1（CNY）":null,"申报总价4（JPY）":null,"申报总价4（CNY）":null,"收件人电话":"182-1758-8628","收件人地址":"上海市闵行区虹梅南路1660弄蔷薇八村39号502室","HAWB#":"860014010055","发件人电话":"03-3684-3676","发件人地址":" 1-1-13,Kameido,Koto-ku,Tokyo","NO":3,"ID":3,"单价2（JPY）":null,"申报总价3（JPY）":null,"单价5（JPY）":null,"申报总价3（CNY）":null,"收货省份":null,"申报总价（JPY）":null,"申报总价（CNY）":null,"总计费重量":3.20,"收件人":"张振泉2","总件数":13,"品名5":null,"品名4":null,"品名3":null,"品名2":null,"品名1":"纸尿片","参考号":null,"发件人":"NAKAGAWA SUMIRE 2","单位5":null,"单位4":null,"单位3":null,"单位2":null,"单位1":null,"件数5":null,"件数4":null,"件数3":3,"件数2":null,"件数1":10},{"鹭路通单号":730291,"发货国家":"日本","单价1（JPY）":null,"申报总价2（JPY）":null,"单价4（JPY）":null,"申报总价2（CNY）":null,"申报总价5（JPY）":null,"华夏单号":200303900789,"申报总价5（CNY）":null,"收货人证件号码":null,"申报总价1（JPY）":null,"单价3（JPY）":null,"申报总价1（CNY）":null,"申报总价4（JPY）":null,"申报总价4（CNY）":null,"收件人电话":"182-1758-8628","收件人地址":"上海市闵行区虹梅南路1660弄蔷薇八村39号502室","HAWB#":"860014010035","发件人电话":"03-3684-3676","发件人地址":" 1-1-13,Kameido,Koto-ku,Tokyo","NO":1,"ID":1,"单价2（JPY）":null,"申报总价3（JPY）":null,"单价5（JPY）":null,"申报总价3（CNY）":null,"收货省份":null,"申报总价（JPY）":null,"申报总价（CNY）":null,"总计费重量":3.20,"收件人":"张振泉","总件数":13,"品名5":null,"品名4":null,"品名3":null,"品名2":null,"品名1":"纸尿片","参考号":null,"发件人":"NAKAGAWA SUMIRE","单位5":null,"单位4":null,"单位3":null,"单位2":null,"单位1":null,"件数5":null,"件数4":null,"件数3":3,"件数2":null,"件数1":10},{"鹭路通单号":730292,"发货国家":"日本","单价1（JPY）":null,"申报总价2（JPY）":null,"单价4（JPY）":null,"申报总价2（CNY）":null,"申报总价5（JPY）":null,"华夏单号":200303900790,"申报总价5（CNY）":null,"收货人证件号码":null,"申报总价1（JPY）":null,"单价3（JPY）":null,"申报总价1（CNY）":null,"申报总价4（JPY）":null,"申报总价4（CNY）":null,"收件人电话":"182-1758-8628","收件人地址":"上海市闵行区虹梅南路1660弄蔷薇八村39号502室","HAWB#":"860014010045","发件人电话":"03-3684-3676","发件人地址":" 1-1-13,Kameido,Koto-ku,Tokyo","NO":2,"ID":2,"单价2（JPY）":null,"申报总价3（JPY）":null,"单价5（JPY）":null,"申报总价3（CNY）":null,"收货省份":null,"申报总价（JPY）":null,"申报总价（CNY）":null,"总计费重量":3.20,"收件人":"张振泉1","总件数":13,"品名5":null,"品名4":null,"品名3":null,"品名2":null,"品名1":"纸尿片","参考号":null,"发件人":"NAKAGAWA SUMIRE 1","单位5":null,"单位4":null,"单位3":null,"单位2":null,"单位1":null,"件数5":null,"件数4":null,"件数3":3,"件数2":null,"件数1":10}]}';
*/
var _reportData = _reportData || '';
var _delay_send = 1000;            //发送打印服务器前延时时长,-1表示不自动发送
var _delay_close = 1000;           //打印完成后关闭窗口的延时时长, -1则表示不关闭
var cfprint_addr = "127.0.0.1";    //打印服务器的地址
var cfprint_port = 54321;          //打印服务器监听端口

var cfprint = null;

//设置对象并连接打印服务器
//如果这个方法不能满足需要，您可以参考该方法自定义
function setup(){
	cfprint = new ws(cfprint_addr, cfprint_port, {
		automaticOpen: false,		//是否自动连接标志(true|false)，默认为true
		reconnectDecay: 1.5,    //自动重连延迟重连速度，数字，默认为1.5
		output:"output",				//指定调试输出div
		protocols:"ws"					//指定通讯协议(ws|wss)，默认为"ws"
	});

	cfprint.onconnecting = function(evn){
    cfprint.log('正与服务器建立连接...', evn);
	}
	cfprint.onopen = function(evn){
    cfprint.log('与服务器连接成功。', evn);
	}
	cfprint.onclose = function(evn){
    cfprint.log('与打印服务器的连接已关闭', evn);
	}

	/**
	* 接收到打印服务器消息
	* 通过该事件，可以获取到打印是否成功
	* 参数：
	* evn: 包含服务器返回信息的事件对象
	*      evn.data:  服务器返回的信息，是一个json字符串，其中：
	*/
	cfprint.onmessage = function(evn){
    cfprint.log('收到消息！"'+evn.data+'"', evn);
    var resp = JSON && JSON.parse(evn.data) || $.parseJSON(evn.data);   //解析服务器返回数据
    if(resp.result == 1){
      if(_delay_close>0)
    		setTimeout(function(){open(location, '_self').close();}, _delay_close); //延时后关闭报表窗口
    }else{
    	alert("Print failed: "+resp.message);
    }
	}

	/**
	 * 捕获到错误事件
	 * 通过该事件在出错时可以判断出错原因
	 * 参数：
	 * evn: 包含错误信息的事件对象
	 *      evn.detail: 是包含错误明细的对象
	 *      evn.detail.message：是错误信息
	 */
	cfprint.onerror = function(evn){
		if(typeof(evn.detail)==="object"){
			if(typeof(evn.detail.message)==="string")
				cfprint.log('遇到一个错误: '+evn.detail.message, evn);
			if(typeof(evn.detail.data)==="string")
				cfprint.log('遇到一个错误: '+evn.detail.message, evn);
		}
		else if(typeof(evn.data)==="string")
			cfprint.log('遇到一个错误: '+evn.data, evn);
		else
    	cfprint.log('遇到一个错误', evn);
	}
	
	//cfprint.open();  //连接到打印服务器，automaticOpen=false时需要这一行
}

/**
 * 发送打印数据到打印服务器
 * 参数： 
 *   str: 发送给打印服务器的数据，支持json字符串和json对象
 */
function sendMsg (json) {
	var _send = function(_msg){
			cfprint.log("SENT: <br/>" +  _msg);
			cfprint.log('正在发送消息...');
			cfprint.send(_msg);
	}
	
	if(!cfprint) setup();
	
	if(cfprint.state()!==cfprint.OPEN) {
		cfprint.log("连接已断开，正在重新连接。");
		//setup();
		cfprint.onopen = function(evn){
    	cfprint.log('与服务器连接成功。', evn);
			_send(json);
		}
		cfprint.open();
	}else{
		_send(json);
	}
}

/*******************************/
//以下是自动打印的代码，如果不是自动打印则不需要

/*无JS框架调用示例
var __doPrint = function(){
	//初始化cfprint对象
	setup();

	//打开连接
	cfprint.open();  //连接到打印服务器，automaticOpen=false时需要这一行

	if(typeof(_reportData) != "undefined" && _reportData != ""){
    if(_delay_send>0){
      setTimeout(function () {
          sendMsg(_reportData);
      }, _delay_send);
    }
	}else {
		cfprint.log("要打印的报表内容为空，取消打印。");
	}
}

if (window.addEventListener)
	window.addEventListener("load", __doPrint, false);
else if (window.attachEvent)
	window.attachEvent("onload", __doPrint);
else window.onload = __doPrint;
*/
/*******无JS框架调用示例结束**********/

/** JQuery 调用示例 **/
jQuery(document).ready(function(){

	//初始化cfprint对象
	setup();

	//打开连接
	cfprint.open();  //连接到打印服务器，automaticOpen=false时需要这一行

	if(typeof(_reportData) != "undefined" && _reportData != ""){
		setTimeout(function () {
			sendMsg(_reportData);
		}, _delay_send);
	}else {
		cfprint.log("要打印的报表内容为空，取消打印。");
	}
});


