<?php
// by Edd Dumbill (C) 1999-2002
// <edd@usefulinc.com>
// $Id: xmlrpcs.inc,v 1.52 2006/01/19 23:48:58 ggiunta Exp $

// Copyright (c) 1999,2000,2002 Edd Dumbill.
// All rights reserved.
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions
// are met:
//
//		* Redistributions of source code must retain the above copyright
//			notice, this list of conditions and the following disclaimer.
//
//		* Redistributions in binary form must reproduce the above
//			copyright notice, this list of conditions and the following
//			disclaimer in the documentation and/or other materials provided
//			with the distribution.
//
//		* Neither the name of the "XML-RPC for PHP" nor the names of its
//			contributors may be used to endorse or promote products derived
//			from this software without specific prior written permission.
//
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
// "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
// LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
// FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
// REGENTS OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
// INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
// (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
// SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
// HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
// STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
// ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
// OF THE POSSIBILITY OF SUCH DAMAGE.

	// XML RPC Server class
	// requires: xmlrpc.inc

	// listMethods: signature was either a string, or nothing.
	// The useless string variant has been removed
	$_xmlrpcs_listMethods_sig=array(array($GLOBALS['xmlrpcArray']));
	$_xmlrpcs_listMethods_doc='This method lists all the methods that the XML-RPC server knows how to dispatch';
	function _xmlrpcs_listMethods($server, $m=null) // if called in plain php values mode, second param is missing
	{

		$outAr=array();
		foreach($server->dmap as $key => $val)
		{
			$outAr[]=&new xmlrpcval($key, 'string');
		}
		if($server->allow_system_funcs)
		{
			foreach($GLOBALS['_xmlrpcs_dmap'] as $key => $val)
			{
				$outAr[]=&new xmlrpcval($key, 'string');
			}
		}
		$v=&new xmlrpcval($outAr, 'array');
		return new xmlrpcresp($v);
	}

	$_xmlrpcs_methodSignature_sig=array(array($GLOBALS['xmlrpcArray'], $GLOBALS['xmlrpcString']));
	$_xmlrpcs_methodSignature_doc='Returns an array of known signatures (an array of arrays) for the method name passed. If no signatures are known, returns a none-array (test for type != array to detect missing signature)';
	function _xmlrpcs_methodSignature($server, $m)
	{
		// let accept as parameter both an xmlrpcval or string
		if (is_object($m))
		{
			$methName=$m->getParam(0);
			$methName=$methName->scalarval();
		}
		else
		{
			$methName=$m;
		}
		if(ereg("^system\.", $methName))
		{
			$dmap=$GLOBALS['_xmlrpcs_dmap']; $sysCall=1;
		}
		else
		{
			$dmap=$server->dmap; $sysCall=0;
		}
		//	print "<!-- ${methName} -->\n";
		if(isset($dmap[$methName]))
		{
			if(isset($dmap[$methName]['signature']))
			{
				$sigs=array();
				foreach($dmap[$methName]['signature'] as $inSig)
				{
					$cursig=array();
					foreach($inSig as $sig)
					{
						$cursig[]=&new xmlrpcval($sig, 'string');
					}
					$sigs[]=&new xmlrpcval($cursig, 'array');
				}
				$r=&new xmlrpcresp(new xmlrpcval($sigs, 'array'));
			}
			else
			{
				// NB: according to the official docs, we should be returning a
				// "none-array" here, which means not-an-array
				$r=&new xmlrpcresp(new xmlrpcval('undef', 'string'));
			}
		}
		else
		{
			$r=&new xmlrpcresp(0,$GLOBALS['xmlrpcerr']['introspect_unknown'], $GLOBALS['xmlrpcstr']['introspect_unknown']);
		}
		return $r;
	}

	$_xmlrpcs_methodHelp_sig=array(array($GLOBALS['xmlrpcString'], $GLOBALS['xmlrpcString']));
	$_xmlrpcs_methodHelp_doc='Returns help text if defined for the method passed, otherwise returns an empty string';
	function _xmlrpcs_methodHelp($server, $m)
	{
		// let accept as parameter both an xmlrpcval or string
		if (is_object($m))
		{
			$methName=$m->getParam(0);
			$methName=$methName->scalarval();
		}
		else
		{
			$methName=$m;
		}
		if(ereg("^system\.", $methName))
		{
			$dmap=$GLOBALS['_xmlrpcs_dmap']; $sysCall=1;
		}
		else
		{
			$dmap=$server->dmap; $sysCall=0;
		}
		// print "<!-- ${methName} -->\n";
		if(isset($dmap[$methName]))
		{
			if(isset($dmap[$methName]['docstring']))
			{
				$r=&new xmlrpcresp(new xmlrpcval($dmap[$methName]['docstring']), 'string');
			}
			else
			{
				$r=&new xmlrpcresp(new xmlrpcval('', 'string'));
			}
		}
		else
		{
			$r=&new xmlrpcresp(0, $GLOBALS['xmlrpcerr']['introspect_unknown'], $GLOBALS['xmlrpcstr']['introspect_unknown']);
		}
		return $r;
	}

	$_xmlrpcs_multicall_sig = array(array($GLOBALS['xmlrpcArray'], $GLOBALS['xmlrpcArray']));
	$_xmlrpcs_multicall_doc = 'Boxcar multiple RPC calls in one request. See http://www.xmlrpc.com/discuss/msgReader$1208 for details';

	function _xmlrpcs_multicall_error($err)
	{
		if(is_string($err))
		{
			$str = $GLOBALS['xmlrpcstr']["multicall_${err}"];
			$code = $GLOBALS['xmlrpcerr']["multicall_${err}"];
		}
		else
		{
			$code = $err->faultCode();
			$str = $err->faultString();
		}
		$struct = array();
		$struct['faultCode'] =& new xmlrpcval($code, 'int');
		$struct['faultString'] =& new xmlrpcval($str, 'string');
		return new xmlrpcval($struct, 'struct');
	}

	function _xmlrpcs_multicall_do_call($server, $call)
	{
		if($call->kindOf() != 'struct')
		{
			return _xmlrpcs_multicall_error('notstruct');
		}
		$methName = @$call->structmem('methodName');
		if(!$methName)
		{
			return _xmlrpcs_multicall_error('nomethod');
		}
		if($methName->kindOf() != 'scalar' || $methName->scalartyp() != 'string')
		{
			return _xmlrpcs_multicall_error('notstring');
		}
		if($methName->scalarval() == 'system.multicall')
		{
			return _xmlrpcs_multicall_error('recursion');
		}

		$params = @$call->structmem('params');
		if(!$params)
		{
			return _xmlrpcs_multicall_error('noparams');
		}
		if($params->kindOf() != 'array')
		{
			return _xmlrpcs_multicall_error('notarray');
		}
		$numParams = $params->arraysize();

		$msg =& new xmlrpcmsg($methName->scalarval());
		for($i = 0; $i < $numParams; $i++)
		{
			if(!$msg->addParam($params->arraymem($i)))
			{
				$i++;
				return _xmlrpcs_multicall_error(new xmlrpcresp(0,
					$GLOBALS['xmlrpcerr']['incorrect_params'],
					$GLOBALS['xmlrpcstr']['incorrect_params'] . ": probable xml error in param " . $i));
			}
		}

		$result = $server->execute($msg);

		if($result->faultCode() != 0)
		{
			return _xmlrpcs_multicall_error($result);		// Method returned fault.
		}

		return new xmlrpcval(array($result->value()), 'array');
	}

	function _xmlrpcs_multicall_do_call_phpvals($server, $call)
	{
		if(!is_array($call))
		{
			return _xmlrpcs_multicall_error('notstruct');
		}
		if(!array_key_exists('methodName', $call))
		{
			return _xmlrpcs_multicall_error('nomethod');
		}
		if (!is_string($call['methodName']))
		{
			return _xmlrpcs_multicall_error('notstring');
		}
		if($call['methodName'] == 'system.multicall')
		{
			return _xmlrpcs_multicall_error('recursion');
		}
		if(!array_key_exists('params', $call))
		{
			return _xmlrpcs_multicall_error('noparams');
		}
		if(!is_array($call['params']))
		{
			return _xmlrpcs_multicall_error('notarray');
		}

		// this is a real dirty and simplistic hack, since we might have received a
		// base64 or datetime values, but they will be listed as strings here...
		$numParams = count($call['params']);
		$pt = array();
		foreach($call['params'] as $val)
			$pt[] = php_2_xmlrpc_type(gettype($val));

		$result = $server->execute($call['methodName'], $call['params'], $pt);

		if($result->faultCode() != 0)
		{
			return _xmlrpcs_multicall_error($result);		// Method returned fault.
		}

		return new xmlrpcval(array($result->value()), 'array');
	}

	function _xmlrpcs_multicall($server, $m)
	{
		$result = array();
		// let accept a plain list of php parameters, beside a single xmlrpc msg object
		if (is_object($m))
		{
			$calls = $m->getParam(0);
			$numCalls = $calls->arraysize();
			for($i = 0; $i < $numCalls; $i++)
			{
				$call = $calls->arraymem($i);
				$result[$i] = _xmlrpcs_multicall_do_call($server, $call);
			}
		}
		else
		{
			//$calls = func_get_args();
			$numCalls=count($m);
			for($i = 0; $i < $numCalls; $i++)
			{
				$result[$i] = _xmlrpcs_multicall_do_call_phpvals($server, $m[$i]);
			}
		}

		return new xmlrpcresp(new xmlrpcval($result, 'array'));
	}

	$GLOBALS['_xmlrpcs_dmap']=array(
		'system.listMethods' => array(
			'function' => '_xmlrpcs_listMethods',
			'signature' => $_xmlrpcs_listMethods_sig,
			'docstring' => $_xmlrpcs_listMethods_doc),
		'system.methodHelp' => array(
			'function' => '_xmlrpcs_methodHelp',
			'signature' => $_xmlrpcs_methodHelp_sig,
			'docstring' => $_xmlrpcs_methodHelp_doc),
		'system.methodSignature' => array(
			'function' => '_xmlrpcs_methodSignature',
			'signature' => $_xmlrpcs_methodSignature_sig,
			'docstring' => $_xmlrpcs_methodSignature_doc),
		'system.multicall' => array(
			'function' => '_xmlrpcs_multicall',
			'signature' => $_xmlrpcs_multicall_sig,
			'docstring' => $_xmlrpcs_multicall_doc
		)
	);

	$GLOBALS['_xmlrpcs_occurred_errors'] = '';
	$GLOBALS['_xmlrpcs_prev_ehandler'] = '';
	/**
	* Error handler used to track errors that occur during server-side execution of PHP code.
	* This allows to report back to the client whether an internal error has occurred or not
	* using an xmlrpc response object, instead of letting the client deal with the html junk
	* that a PHP execution error on the server generally entails.
	*
	* NB: in fact a user defined error handler can only handle WARNING, NOTICE and USER_* errors.
	*
	*/
	function _xmlrpcs_errorHandler($errcode, $errstring, $filename=null, $lineno=null, $context=null)
	{
		//if($errcode != E_NOTICE && $errcode != E_WARNING && $errcode != E_USER_NOTICE && $errcode != E_USER_WARNING)
		if($errcode != 2048) // do not use E_STRICT by name, since on PHP 4 it will not be defined
		{
			$GLOBALS['_xmlrpcs_occurred_errors'] = $GLOBALS['_xmlrpcs_occurred_errors'] . $errstring . "\n";
		}
		// Try to avoid as much as possible disruption to the previous error handling
		// mechanism in place
		if($GLOBALS['_xmlrpcs_prev_ehandler'] == '')
		{
			// The previous error handler was the default: all we should do is log error
			// to teh default error log (if level high enough)
			if(ini_get('log_errors') && (intval(ini_get('error_reporting')) & $errcode))
			{
				error_log($errstring);
			}
		}
		else
		{
			// Pass control on to previous error handler, trying to avoid loops...
			if($GLOBALS['_xmlrpcs_prev_ehandler'] != '_xmlrpcs_errorHandler')
			{
				// NB: this code will NOT work on php < 4.0.2: only 2 params were used for error handlers
				if(is_array($GLOBALS['_xmlrpcs_prev_ehandler']))
				{
					$GLOBALS['_xmlrpcs_prev_ehandler'][0]->$GLOBALS['_xmlrpcs_prev_ehandler'][1]($errcode, $errstring, $filename, $lineno, $context);
				}
				else
				{
					$GLOBALS['_xmlrpcs_prev_ehandler']($errcode, $errstring, $filename, $lineno, $context);
				}
			}
		}
	}

	$GLOBALS['_xmlrpc_debuginfo']='';

	/**
	* Add a string to the debug info that can be later seralized by the server
	* as part of the response message.
	* Note that for best compatbility, the debug string should be encoded using
	* the $GLOBALS['xmlrpc_internalencoding'] character set.
	* @param string $m
	* @access public
	*/
	function xmlrpc_debugmsg($m)
	{
		$GLOBALS['_xmlrpc_debuginfo'] .= $m . "\n";
	}

	class xmlrpc_server
	{
		/// array defining php functions exposed as xmlrpc methods by this server
		var $dmap=array();
		/**
		* Defines how functions in dmap will be invokde: either using an xmlrpc msg object
		* or plain php values.
		* valid strings are 'xmlrpcvals' or 'phpvals'
		*/
		var $functions_parameters_type='xmlrpcvals';
		/// controls wether the server is going to echo debugging messages back to the client as comments in response body. valid values: 0,1,2,3
		var $debug = 1;
		/**
		* When set to true, it will enable HTTP compression of the response, in case
		* the client has declared its support for compression in the request.
		*/
		var $compress_response = false;
		/**
		* List of http compression methods accepted by the server for requests.
		* NB: PHP supports deflate, gzip compressions out of the box if compiled w. zlib
		*/
		var $accepted_compression = array();
		/// shall we serve calls to system.* methods?
		var $allow_system_funcs = true;
		/// list of charset encodings natively accepted for requests
		var $accepted_charset_encodings = array();
		/**
		* charset encoding to be used for response.
		* NB: if we can, we will convert the generated response from internal_encoding to the intended one.
		* can be: a supported xml encoding (only UTF-8 and ISO-8859-1 at present, unless mbstring is enabled),
		* null (leave unspecified in response, convert output stream to US_ASCII),
		* 'default' (use xmlrpc library default as specified in xmlrpc.inc, convert outpt stream if needed),
		* or 'auto' (use client-specified charset encoding or same as request if request headers do not specify it (unless request is US-ASCII: then use library default anyway).
		* NB: pretty dangerous if you accept every charset and do not have mbstring enabled)
		*/
		var $response_charset_encoding = '';
		var $xml_header = "<?xml version=\"1.0\" ?>\n";
		/// storage for internal debug info
		var $debug_info = '';

		/**
		* @param array $dispmap the dispatch map withd efinition of exposed services
		* @param boolean $servicenow set to false to prevent the server from runnung upon construction
		*/
		function xmlrpc_server($dispMap=null, $serviceNow=true)
		{
			// if ZLIB is enabled, let the server by default accept compressed requests,
			// and compress responses sent to clients that support them
			if(function_exists('gzinflate'))
			{
				$this->accepted_compression = array('gzip', 'deflate');
				$this->compress_response = true;
			}

			// by default the xml parser can support these 3 charset encodings
			$this->accepted_charset_encodings = array('UTF-8', 'ISO-8859-1', 'US-ASCII');

			// dispMap is a dispatch array of methods
			// mapped to function names and signatures
			// if a method
			// doesn't appear in the map then an unknown
			// method error is generated
			/* milosch - changed to make passing dispMap optional.
			 * instead, you can use the class add_to_map() function
			 * to add functions manually (borrowed from SOAPX4)
			 */
			if($dispMap)
			{
				$this->dmap = $dispMap;
				if($serviceNow)
				{
					$this->service();
				}
			}
		}

		/**
		* Set debug level of server.
		* @param integer $in debug lvl: determines info added to xmlrpc responses (as xml comments)
		* 0 = no debug info,
		* 1 = msgs set from user with debugmsg(),
		* 2 = add complete xmlrpc request (headers and body),
		* 3 = add also all processing warnings happened during method processing
		* (NB: this involves setting a custom error handler, and might interfere
		* with the standard processing of the php function exposed as method. In
		* particular, triggering an USER_ERROR level error will not halt script
		* execution anymore, but just end up logged in the xmlrpc response)
		* Note that info added at elevel 2 and 3 will be base64 encoded
		*/
		function setDebug($in)
		{
			$this->debug=$in;
		}

		/**
		* Return a string with the serialized representation of all debug info
		* @param string $charset_encoding the target charset encoding for the serialization
		* @return string an XML comment (or two)
		*/
		function serializeDebug($charset_encoding='')
		{
			// Tough encoding problem: which internal charset should we assume for debug info?
			// It might contain a copy of raw data received from client, ie with unknown encoding,
			// intermixed with php generated data and user generated data...
			// so we split it: system debug is base 64 encoded,
			// user debug info should be encoded by the end user using the INTERNAL_ENCODING
			$out = '';
			if ($this->debug_info != '') {
				$out .= "<!-- SERVER DEBUG INFO (BASE64 ENCODED):\n".base64_encode($this->debug_info)."\n-->\n";
			}
			if($GLOBALS['_xmlrpc_debuginfo']!='')
			{

				$out .= "<!-- DEBUG INFO:\n" . xmlrpc_encode_entitites(str_replace('--', '_-', $GLOBALS['_xmlrpc_debuginfo']), $GLOBALS['xmlrpc_internalencoding'], $charset_encoding) . "\n-->\n";
				// NB: a better solution MIGHT be to use CDATA, but we need to insert it
				// into return payload AFTER the beginning tag
				//$out .= "<![CDATA[ DEBUG INFO:\n\n" . str_replace(']]>', ']_]_>', $GLOBALS['_xmlrpc_debuginfo']) . "\n]]>\n";
			}
			return $out;
		}

		/**
		* Execute the xmlrpc request, printing the response
		* @param string $data the request body. If null, the http POST request will be examined
		*/
		function service($data=null)
		{
			if ($data === null) {
				$data = isset($GLOBALS['HTTP_RAW_POST_DATA']) ? $GLOBALS['HTTP_RAW_POST_DATA'] : '';
			}

			// reset internal debug info
			$this->debug_info = '';

			// Echo back what we received, before parsing it
			if($this->debug > 1)
			{
				$this->debugmsg("+++GOT+++\n" . $data . "\n+++END+++");
			}

			$r = $this->parseRequestHeaders($data, $req_charset, $resp_charset, $resp_encoding);
			if (!$r)
			{
				$r=$this->parseRequest($data, $req_charset);
			}

			if($this->debug > 2 && $GLOBALS['_xmlrpcs_occurred_errors'])
			{
				$this->debugmsg("+++PROCESSING ERRORS AND WARNINGS+++\n" .
					$GLOBALS['_xmlrpcs_occurred_errors'] . "+++END+++");
			}

			//$payload='<?xml version="1.0" encoding="' . $GLOBALS['xmlrpc_defencoding'] . '"?' . '>' . "\n"
			$payload=$this->xml_header;
			if($this->debug > 0)
			{

				//$payload = $payload . "<methodResponse>\n" . $this->serializeDebug();
				//$payload = $payload . substr($r->serialize(), 17);
				$payload = $payload . $this->serializeDebug($resp_charset);
			}
			//else
			//{
			$payload = $payload . $r->serialize($resp_charset);
			//}


			// if we get a warning/error that has output some text before here, then we cannot
			// add a new header. We cannot say we are sending xml, either...
			if(!headers_sent())
			{
				header('Content-Type: '.$r->content_type);
				// we do not know if client actually told us an accepted charset, but if he did
				// we have to tell him what we did
				header("Vary: Accept-Charset");

				// http compression of output
				if($this->compress_response && function_exists('gzencode') && $resp_encoding != '')
				{
					if(strstr($resp_encoding, 'gzip'))
					{
						$payload = gzencode($payload);
						header("Content-Encoding: gzip");
						header("Vary: Accept-Encoding");
					}
					elseif (strstr($resp_encoding, 'deflate'))
					{
						$payload = gzdeflate($payload);
						header("Content-Encoding: deflate");
						header("Vary: Accept-Encoding");
					}
				}

				header('Content-Length: ' . (int)strlen($payload));
			}
			else
			{
				//print "Internal server error: headers sent before PHP response"
			}

			print $payload;
		}

		/**
		* Add a method to the dispatch map
		* @param string $methodname the name with which the method will be made available
		* @param string $function the php function that will get invoked
		* @param array $sig the array of valid method signatures
		* @param string $doc method documentation
		*/
		function add_to_map($methodname,$function,$sig,$doc='')
		{
			$this->dmap[$methodname] = array(
				'function'	=> $function,
				'signature' => $sig,
				'docstring' => $doc
			);
		}

		/**
		* Verify type and number of parameters received against a list of known signatures
		* @param array $in array of either xmlrpcval objects or xmlrpc type definitions
		* @param array $sig array of known signatures to match against
		* @access private
		*/
		function verifySignature($in, $sig)
		{
			// check each possible signature in turn
			if (is_object($in))
			{
				$numParams = $in->getNumParams();
			}
			else
			{
				$numParams = sizeof($in);
			}
			foreach($sig as $cursig)
			{
				if(sizeof($cursig)==$numParams+1)
				{
					$itsOK=1;
					for($n=0; $n<$numParams; $n++)
					{
						if (is_object($in))
						{
							$p=$in->getParam($n);
							if($p->kindOf() == 'scalar')
							{
								$pt=$p->scalartyp();
							}
							else
							{
								$pt=$p->kindOf();
							}
						}
						else
						{
							$pt= $in[$n] == 'i4' ? 'int' : $in[$n]; // dispatch maps never use i4...
						}

						// param index is $n+1, as first member of sig is return type
						if($pt != $cursig[$n+1] && $cursig[$n+1] != $GLOBALS['xmlrpcValue'])
						{
							$itsOK=0;
							$pno=$n+1;
							$wanted=$cursig[$n+1];
							$got=$pt;
							break;
						}
					}
					if($itsOK)
					{
						return array(1,'');
					}
				}
			}
			if(isset($wanted))
			{
				return array(0, "Wanted ${wanted}, got ${got} at param ${pno}");
			}
			else
			{
				return array(0, "No method signature matches number of parameters");
			}
		}

		/**
		* Parse http headers received along with xmlrpc request. If needed, inflate request
		* @return null on success or an xmlrpcresp
		* @access private
		*/
		function parseRequestHeaders(&$data, &$req_encoding, &$resp_encoding, &$resp_compression)
		{
			// Play nice to PHP 4.0.x: superglobals were not yet invented...
			if(!isset($_SERVER))
			{
				$_SERVER = $GLOBALS['HTTP_SERVER_VARS'];
			}

			if($this->debug > 1)
			{
				if(function_exists('getallheaders'))
				{
					$this->debugmsg(''); // empty line
					foreach(getallheaders() as $name => $val)
					{
						$this->debugmsg("HEADER: $name: $val");
					}
				}

			}

			if(isset($_SERVER['HTTP_CONTENT_ENCODING']))
			{
				$content_encoding = $_SERVER['HTTP_CONTENT_ENCODING'];
			}
			else
			{
				$content_encoding = '';
			}

			// check if request body has been compressed and decompress it
			if($content_encoding != '' && strlen($data))
			{
				if($content_encoding == 'deflate' || $content_encoding == 'gzip')
				{
					// if decoding works, use it. else assume data wasn't gzencoded
					if(function_exists('gzinflate') && in_array($content_encoding, $this->accepted_compression))
					{
						if($content_encoding == 'deflate' && $degzdata = @gzinflate($data))
						{
							$data = $degzdata;
							if($this->debug > 1)
							{
								$this->debugmsg("\n+++INFLATED REQUEST+++[".strlen($data)." chars]+++\n" . $data . "\n+++END+++");
							}
						}
						elseif($content_encoding == 'gzip' && $degzdata = @gzinflate(substr($data, 10)))
						{
							$data = $degzdata;
							if($this->debug > 1)
								$this->debugmsg("+++INFLATED REQUEST+++[".strlen($data)." chars]+++\n" . $data . "\n+++END+++");
						}
						else
						{
							$r =& new xmlrpcresp(0, $GLOBALS['xmlrpcerr']['server_decompress_fail'], $GLOBALS['xmlrpcstr']['server_decompress_fail']);
							return $r;
						}
					}
					else
					{
						//error_log('The server sent deflated data. Your php install must have the Zlib extension compiled in to support this.');
						$r =& new xmlrpcresp(0, $GLOBALS['xmlrpcerr']['server_cannot_decompress'], $GLOBALS['xmlrpcstr']['server_cannot_decompress']);
						return $r;
					}
				}
			}

			// check if client specified accepted charsets, and if we know how to fulfill
			// the request
			if ($this->response_charset_encoding == 'auto')
			{
				$resp_encoding = '';
				if (isset($_SERVER['HTTP_ACCEPT_CHARSET']))
				{
					// here we should check if we can match the client-requested encoding
					// with the encodings we know we can generate.
					/// @todo we should parse q=0.x preferences instead of getting first charset specified...
					$client_accepted_charsets = split(',', strtoupper($_SERVER['HTTP_ACCEPT_CHARSET']));
					// Give preference to internal encoding
					$known_charsets = array($this->internal_encoding, 'UTF-8', 'ISO-8859-1', 'US-ASCII');
					foreach ($known_charsets as $charset)
					{
						foreach ($client_accepted_charsets as $accepted)
							if (strpos($accepted, $charset) === 0)
							{
								$resp_encoding = $charset;
								break;
							}
						if ($resp_encoding)
							break;
					}
				}
			}
			else
			{

				$resp_encoding = $this->response_charset_encoding;
			}

			if (isset($_SERVER['HTTP_ACCEPT_ENCODING']))
			{
				$resp_compression = $_SERVER['HTTP_ACCEPT_ENCODING'];
			}
			else
			{
				$resp_compression = '';
			}

			// 'guestimate' request encoding
			/// @todo check if mbstring is enabled and automagic input conversion is on: it might mingle with this check???
			$req_encoding = guess_encoding(isset($_SERVER['HTTP_CONTENT_TYPE']) ? $_SERVER['HTTP_CONTENT_TYPE'] : '',
				$data);

			return null;
		}

		/**
		* Parse an xml chunk containing an xmlrpc request and execute the corresponding
		* php function registered with the server
		* @param string $data the xml request
		* @param string $req_encoding (optional) the charset encoding of the xml request
		* @return xmlrpcresp
		* @access private
		*/
		function parseRequest($data, $req_encoding='')
		{
			// 2005/05/07 commented and moved into caller function code
			//if($data=='')
			//{
			//	$data=$GLOBALS['HTTP_RAW_POST_DATA'];
			//}


			// G. Giunta 2005/02/13: we do NOT expect to receive html entities
			// so we do not try to convert them into xml character entities
			//$data = xmlrpc_html_entity_xlate($data);

			$GLOBALS['_xh']=array();
			$GLOBALS['_xh']['isf']=0;
			$GLOBALS['_xh']['isf_reason']='';
			$GLOBALS['_xh']['params']=array();
			$GLOBALS['_xh']['pt']=array();
			$GLOBALS['_xh']['stack']=array();
			$GLOBALS['_xh']['valuestack'] = array();
			$GLOBALS['_xh']['method']='';

			// decompose incoming XML into request structure
			if ($req_encoding != '')
			{
				if (!in_array($req_encoding, array('UTF-8', 'ISO-8859-1', 'US-ASCII')))
				// the following code might be better for mb_string enabled installs, but
				// makes the lib about 200% slower...
				//if (!is_valid_charset($req_encoding, array('UTF-8', 'ISO-8859-1', 'US-ASCII')))
				{
					error_log('XML-RPC: xmlrpc_server::parseRequest: invalid charset encoding of received request: '.$req_encoding);
					$req_encoding = $GLOBALS['xmlrpc_defencoding'];
				}
				$parser = xml_parser_create($req_encoding);
			}
			else
			{
				$parser = xml_parser_create();
			}

			xml_parser_set_option($parser, XML_OPTION_CASE_FOLDING, true);
			// G. Giunta 2005/02/13: PHP internally uses ISO-8859-1, so we have to tell
			// the xml parser to give us back data in the expected charset
			xml_parser_set_option($parser, XML_OPTION_TARGET_ENCODING, $GLOBALS['xmlrpc_internalencoding']);

			if ($this->functions_parameters_type == 'phpvals')
				xml_set_element_handler($parser, 'xmlrpc_se', 'xmlrpc_ee_fast');
			else
				xml_set_element_handler($parser, 'xmlrpc_se', 'xmlrpc_ee');
			xml_set_character_data_handler($parser, 'xmlrpc_cd');
			xml_set_default_handler($parser, 'xmlrpc_dh');
			if(!xml_parse($parser, $data, 1))
			{
				// return XML error as a faultCode
				$r=&new xmlrpcresp(0,
				$GLOBALS['xmlrpcerrxml']+xml_get_error_code($parser),
				sprintf('XML error: %s at line %d',
					xml_error_string(xml_get_error_code($parser)),
					xml_get_current_line_number($parser)));
				xml_parser_free($parser);
			}
			elseif ($GLOBALS['_xh']['isf'])
			{
				xml_parser_free($parser);
				$r=&new xmlrpcresp(0,
					$GLOBALS['xmlrpcerr']['invalid_request'],
					$GLOBALS['xmlrpcstr']['invalid_request'] . ' ' . $GLOBALS['_xh']['isf_reason']);
			}
			else
			{
				xml_parser_free($parser);
				if ($this->functions_parameters_type == 'phpvals')
				{
					if($this->debug > 1)
					{
						$this->debugmsg("\n+++PARSED+++\n".var_export($GLOBALS['_xh']['params'], true)."\n+++END+++");
					}
					$r = $this->execute($GLOBALS['_xh']['method'], $GLOBALS['_xh']['params'], $GLOBALS['_xh']['pt']);
				}
				else
				{
					// build an xmlrpcmsg object with data parsed from xml
					$m=&new xmlrpcmsg($GLOBALS['_xh']['method']);
					// now add parameters in
					for($i=0; $i<sizeof($GLOBALS['_xh']['params']); $i++)
					{
						$m->addParam($GLOBALS['_xh']['params'][$i]);
					}

					if($this->debug > 1)
					{
						$this->debugmsg("\n+++PARSED+++\n".var_export($m, true)."\n+++END+++");
					}

					$r = $this->execute($m);
				}
			}
			return $r;
		}

		/**
		* Execute a method invoked by the client, checking parameters used
		* @param mixed $m either an xmlrpcmsg obj or a method name
		* @param array $params array with method parameters as php types (if m is method name only)
		* @param array $paramtypes array with xmlrpc types of method parameters (if m is method name only)
		* @return xmlrpcresp
		*/
		function execute($m, $params=null, $paramtypes=null)
		{
			if (is_object($m))
			{
				$methName = $m->method();
			}
			else
			{
				$methName = $m;
			}
			$sysCall = $this->allow_system_funcs && ereg("^system\.", $methName);
			$dmap = $sysCall ? $GLOBALS['_xmlrpcs_dmap'] : $this->dmap;

			if(!isset($dmap[$methName]['function']))
			{
				// No such method
				return new xmlrpcresp(0,
					$GLOBALS['xmlrpcerr']['unknown_method'],
					$GLOBALS['xmlrpcstr']['unknown_method']);
			}

			// Check signature
			if(isset($dmap[$methName]['signature']))
			{
				$sig = $dmap[$methName]['signature'];
				if (is_object($m))
				{
					list($ok, $errstr) = $this->verifySignature($m, $sig);
				}
				else
				{
				list($ok, $errstr) = $this->verifySignature($paramtypes, $sig);
				}
				if(!$ok)
				{
					// Didn't match.
					return new xmlrpcresp(
						0,
						$GLOBALS['xmlrpcerr']['incorrect_params'],
						$GLOBALS['xmlrpcstr']['incorrect_params'] . ": ${errstr}"
					);
				}
			}

			$func = $dmap[$methName]['function'];
			// let the 'class::function' syntax be accepted in dispatch maps
			if(is_string($func) && strpos($func, '::'))
			{
				$func = explode('::', $func);
			}
			// verify that function to be invoked is in fact callable
			if(!is_callable($func))
			{
				return new xmlrpcresp(
					0,
					$GLOBALS['xmlrpcerr']['server_error'],
					$GLOBALS['xmlrpcstr']['server_error'] . ": no function matches method"
				);
			}

			// If debug level is 3, we should catch all errors generated during
			// processing of user function, and log them as part of response
			if($this->debug > 2)
			{
				$GLOBALS['_xmlrpcs_prev_ehandler'] = set_error_handler('_xmlrpcs_errorHandler');
			}
			if (is_object($m))
			{
				if($sysCall)
				{
					$r = call_user_func($func, $this, $m);
				}
				else
				{
					$r = call_user_func($func, $m);
				}
			}
			else
			{
				// call a 'plain php' function
				if($sysCall)
				{
					array_unshift($params, $this);
					$r = call_user_func_array($func,$params);
				}
				else
				{
					$r = call_user_func_array($func, $params);
				}
				// the return type can be either an xmlrpcresp object or a plain php value...
				if (!is_a($r, 'xmlrpcresp'))
				{
					// what should we assume here about automatic encoding of datetimes
					// and php classes instances???
					$r = new xmlrpcresp(php_xmlrpc_encode($r, array('auto_dates')));
				}
			}
			if($this->debug > 2)
			{
				// note: restore the error handler we found before calling the
				// user func, even if it has been changed inside the func itself
				if($GLOBALS['_xmlrpcs_prev_ehandler'])
				{
					set_error_handler($GLOBALS['_xmlrpcs_prev_ehandler']);
				}
				else
				{
					restore_error_handler();
				}
			}
			return $r;
		}

		/**
		* add a string to the 'internal debug message' (separate from 'user debug message')
		* @param string $strings
		* @access private
		*/
		function debugmsg($string)
		{
			$this->debug_info .= $string."\n";
		}

		/**
		* A debugging routine: just echoes back the input packet as a string value
		* DEPRECATED!
		*/
		function echoInput()
		{
			$r=&new xmlrpcresp(new xmlrpcval( "'Aha said I: '" . $GLOBALS['HTTP_RAW_POST_DATA'], 'string'));
			print $r->serialize();
		}
	}
?>