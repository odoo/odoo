<?php					// -*-c++-*-
// by Edd Dumbill (C) 1999-2002
// <edd@usefulinc.com>
// $Id: xmlrpc.inc,v 1.113 2006/01/22 23:55:57 ggiunta Exp $


// Copyright (c) 1999,2000,2002 Edd Dumbill.
// All rights reserved.
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions
// are met:
//
//    * Redistributions of source code must retain the above copyright
//      notice, this list of conditions and the following disclaimer.
//
//    * Redistributions in binary form must reproduce the above
//      copyright notice, this list of conditions and the following
//      disclaimer in the documentation and/or other materials provided
//      with the distribution.
//
//    * Neither the name of the "XML-RPC for PHP" nor the names of its
//      contributors may be used to endorse or promote products derived
//      from this software without specific prior written permission.
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

	if(!function_exists('xml_parser_create'))
	{
		// For PHP 4 onward, XML functionality is always compiled-in on windows:
		// no more need to dl-open it. It might have been compiled out on *nix...
		if(strtoupper(substr(PHP_OS, 0, 3) != 'WIN'))
		{
			dl('xml.so');
		}
	}

	// Try to be backward compat with php < 4.2 (are we not being nice ?)
	if(substr(phpversion(), 0, 3) == '4.0' || @version_compare(substr(phpversion(), 0, 3) == '4.1'))
	{
		// give an opportunity to user to specify where to include other files from
		if(!defined('PHP_XMLRPC_COMPAT_DIR'))
		{
			define('PHP_XMLRPC_COMPAT_DIR',dirname(__FILE__).'/compat/');
		}
		if(substr(phpversion(), 0, 3) == '4.0')
		{
			include(PHP_XMLRPC_COMPAT_DIR."is_scalar.php");
			include(PHP_XMLRPC_COMPAT_DIR."array_key_exists.php");
			include(PHP_XMLRPC_COMPAT_DIR."version_compare.php");
		}
		include(PHP_XMLRPC_COMPAT_DIR."var_export.php");
		include(PHP_XMLRPC_COMPAT_DIR."is_a.php");
	}

	// G. Giunta 2005/01/29: declare global these variables,
	// so that xmlrpc.inc will work even if included from within a function
	// Milosch: 2005/08/07 - explicitly request these via $GLOBALS where used.
	$GLOBALS['xmlrpcI4']='i4';
	$GLOBALS['xmlrpcInt']='int';
	$GLOBALS['xmlrpcBoolean']='boolean';
	$GLOBALS['xmlrpcDouble']='double';
	$GLOBALS['xmlrpcString']='string';
	$GLOBALS['xmlrpcDateTime']='dateTime.iso8601';
	$GLOBALS['xmlrpcBase64']='base64';
	$GLOBALS['xmlrpcArray']='array';
	$GLOBALS['xmlrpcStruct']='struct';
	$GLOBALS['xmlrpcValue']='undefined';

	$GLOBALS['xmlrpcTypes']=array(
		$GLOBALS['xmlrpcI4']       => 1,
		$GLOBALS['xmlrpcInt']      => 1,
		$GLOBALS['xmlrpcBoolean']  => 1,
		$GLOBALS['xmlrpcString']   => 1,
		$GLOBALS['xmlrpcDouble']   => 1,
		$GLOBALS['xmlrpcDateTime'] => 1,
		$GLOBALS['xmlrpcBase64']   => 1,
		$GLOBALS['xmlrpcArray']    => 2,
		$GLOBALS['xmlrpcStruct']   => 3
	);

	$GLOBALS['xmlrpc_valid_parents'] = array(
		'BOOLEAN' => array('VALUE'),
		'I4' => array('VALUE'),
		'INT' => array('VALUE'),
		'STRING' => array('VALUE'),
		'DOUBLE' => array('VALUE'),
		'DATETIME.ISO8601' => array('VALUE'),
		'BASE64' => array('VALUE'),
		'ARRAY' => array('VALUE'),
		'STRUCT' => array('VALUE'),
		'PARAM' => array('PARAMS'),
		'METHODNAME' => array('METHODCALL'),
		'PARAMS' => array('METHODCALL', 'METHODRESPONSE'),
		'MEMBER' => array('STRUCT'),
		'NAME' => array('MEMBER'),
		'DATA' => array('ARRAY'),
		'FAULT' => array('METHODRESPONSE'),
		'VALUE' => array('MEMBER', 'DATA', 'PARAM', 'FAULT'),
	);

	$GLOBALS['xmlEntities']=array(
		'amp'  => '&',
		'quot' => '"',
		'lt'   => '<',
		'gt'   => '>',
		'apos' => "'"
	);

	// tables used for transcoding different charsets into us-ascii xml

	$GLOBALS['xml_iso88591_Entities']=array();
	$GLOBALS['xml_iso88591_Entities']['in'] = array();
	$GLOBALS['xml_iso88591_Entities']['out'] = array();
	for ($i = 0; $i < 32; $i++)
	{

		$GLOBALS['xml_iso88591_Entities']['in'][] = chr($i);
		$GLOBALS['xml_iso88591_Entities']['out'][] = "&#$i;";
	}
	for ($i = 160; $i < 256; $i++)
	{
		$GLOBALS['xml_iso88591_Entities']['in'][] = chr($i);
		$GLOBALS['xml_iso88591_Entities']['out'][] = "&#$i;";
	}

	/// @todo add to iso table the characters from cp_1252 range, i.e. 128 to 159.
	/// These will NOT be present in true ISO-8859-1, but will save the unwary
	/// windows user from sending junk.
/*
$cp1252_to_htmlent =
  array(
   '\x80'=>'&#x20AC;', '\x81'=>'?', '\x82'=>'&#x201A;', '\x83'=>'&#x0192;',
   '\x84'=>'&#x201E;', '\x85'=>'&#x2026;', '\x86'=>'&#x2020;', \x87'=>'&#x2021;',
   '\x88'=>'&#x02C6;', '\x89'=>'&#x2030;', '\x8A'=>'&#x0160;', '\x8B'=>'&#x2039;',
   '\x8C'=>'&#x0152;', '\x8D'=>'?', '\x8E'=>'&#x017D;', '\x8F'=>'?',
   '\x90'=>'?', '\x91'=>'&#x2018;', '\x92'=>'&#x2019;', '\x93'=>'&#x201C;',
   '\x94'=>'&#x201D;', '\x95'=>'&#x2022;', '\x96'=>'&#x2013;', '\x97'=>'&#x2014;',
   '\x98'=>'&#x02DC;', '\x99'=>'&#x2122;', '\x9A'=>'&#x0161;', '\x9B'=>'&#x203A;',
   '\x9C'=>'&#x0153;', '\x9D'=>'?', '\x9E'=>'&#x017E;', '\x9F'=>'&#x0178;'
  );
*/

	$GLOBALS['xmlrpcerr']['unknown_method']=1;
	$GLOBALS['xmlrpcstr']['unknown_method']='Unknown method';
	$GLOBALS['xmlrpcerr']['invalid_return']=2;
	$GLOBALS['xmlrpcstr']['invalid_return']='Invalid return payload: enable debugging to examine incoming payload';
	$GLOBALS['xmlrpcerr']['incorrect_params']=3;
	$GLOBALS['xmlrpcstr']['incorrect_params']='Incorrect parameters passed to method';
	$GLOBALS['xmlrpcerr']['introspect_unknown']=4;
	$GLOBALS['xmlrpcstr']['introspect_unknown']="Can't introspect: method unknown";
	$GLOBALS['xmlrpcerr']['http_error']=5;
	$GLOBALS['xmlrpcstr']['http_error']="Didn't receive 200 OK from remote server.";
	$GLOBALS['xmlrpcerr']['no_data']=6;
	$GLOBALS['xmlrpcstr']['no_data']='No data received from server.';
	$GLOBALS['xmlrpcerr']['no_ssl']=7;
	$GLOBALS['xmlrpcstr']['no_ssl']='No SSL support compiled in.';
	$GLOBALS['xmlrpcerr']['curl_fail']=8;
	$GLOBALS['xmlrpcstr']['curl_fail']='CURL error';
	$GLOBALS['xmlrpcerr']['invalid_request']=15;
	$GLOBALS['xmlrpcstr']['invalid_request']='Invalid request payload';
	$GLOBALS['xmlrpcerr']['no_curl']=16;
	$GLOBALS['xmlrpcstr']['no_curl']='No CURL support compiled in.';
	$GLOBALS['xmlrpcerr']['server_error']=17;
	$GLOBALS['xmlrpcstr']['server_error']='Internal server error';
	$GLOBALS['xmlrpcerr']['multicall_error']=18;
	$GLOBALS['xmlrpcstr']['multicall_error']='Received from server invalid multicall response';

	$GLOBALS['xmlrpcerr']['multicall_notstruct'] = 9;
	$GLOBALS['xmlrpcstr']['multicall_notstruct'] = 'system.multicall expected struct';
	$GLOBALS['xmlrpcerr']['multicall_nomethod']  = 10;
	$GLOBALS['xmlrpcstr']['multicall_nomethod']  = 'missing methodName';
	$GLOBALS['xmlrpcerr']['multicall_notstring'] = 11;
	$GLOBALS['xmlrpcstr']['multicall_notstring'] = 'methodName is not a string';
	$GLOBALS['xmlrpcerr']['multicall_recursion'] = 12;
	$GLOBALS['xmlrpcstr']['multicall_recursion'] = 'recursive system.multicall forbidden';
	$GLOBALS['xmlrpcerr']['multicall_noparams']  = 13;
	$GLOBALS['xmlrpcstr']['multicall_noparams']  = 'missing params';
	$GLOBALS['xmlrpcerr']['multicall_notarray']  = 14;
	$GLOBALS['xmlrpcstr']['multicall_notarray']  = 'params is not an array';

	$GLOBALS['xmlrpcerr']['cannot_decompress']=103;
	$GLOBALS['xmlrpcstr']['cannot_decompress']='Received from server compressed HTTP and cannot decompress';
	$GLOBALS['xmlrpcerr']['decompress_fail']=104;
	$GLOBALS['xmlrpcstr']['decompress_fail']='Received from server invalid compressed HTTP';
	$GLOBALS['xmlrpcerr']['dechunk_fail']=105;
	$GLOBALS['xmlrpcstr']['dechunk_fail']='Received from server invalid chunked HTTP';
	$GLOBALS['xmlrpcerr']['server_cannot_decompress']=106;
	$GLOBALS['xmlrpcstr']['server_cannot_decompress']='Received from client compressed HTTP request and cannot decompress';
	$GLOBALS['xmlrpcerr']['server_decompress_fail']=107;
	$GLOBALS['xmlrpcstr']['server_decompress_fail']='Received from client invalid compressed HTTP request';

	// The charset encoding used by the server for received messages and
	// by the client for received responses when received charset cannot be determined
	// or is not supported
	$GLOBALS['xmlrpc_defencoding']='UTF-8';
	// The encoding used internally by PHP.
	// String values received as xml will be converted to this, and php strings will be converted to xml

	// as if having been coded with this
	$GLOBALS['xmlrpc_internalencoding']='ISO-8859-1';

	$GLOBALS['xmlrpcName']='XML-RPC for PHP';
	$GLOBALS['xmlrpcVersion']='2.0RC3';

	// let user errors start at 800
	$GLOBALS['xmlrpcerruser']=800;
	// let XML parse errors start at 100
	$GLOBALS['xmlrpcerrxml']=100;

	// formulate backslashes for escaping regexp
	$GLOBALS['xmlrpc_backslash']=chr(92).chr(92);

	// used to store state during parsing
	// quick explanation of components:
	//   ac - used to accumulate values
	//   isf - used to indicate a fault
	//   lv - used to indicate "looking for a value": implements
	//        the logic to allow values with no types to be strings
	//   params - used to store parameters in method calls
	//   method - used to store method name
	//   stack - array with genealogy of xml elements names:
	//           used to validate nesting of xmlrpc elements

	$GLOBALS['_xh']=null;

	/**
	* Convert a string to the correct XML representation in a target charset
	* To help correct communication of non-ascii chars inside strings, regardless
	* of the charset used when sending requests, parsing them, sending responses
	* and parsing responses, an option is to convert all non-ascii chars present in the message
	* into their equivalent 'charset entity'. Charset entities enumerated this way
	* are independent of the charset encoding used to transmit them, and all XML
	* parsers are bound to understand them.
	* Note that in the std case we are not sending a charset encoding mime type
	* along with http headers, so we are bound by RFC 3023 to emit strict us-ascii.
	*
	* @todo do a bit of basic benchmarking (strtr vs. str_replace)
	* @todo	make usage of iconv() or recode_string() or mb_string() where available
	*/
	function xmlrpc_encode_entitites($data, $src_encoding='', $dest_encoding='')
	{
		if ($src_encoding == '')
		{
			// lame, but we know no better...
			$src_encoding = $GLOBALS['xmlrpc_internalencoding'];
		}
		//if ($dest_encoding == '')
		//{
		//	// lame, but we know no better...
		//	$dest_encoding = 'US-ASCII';
		//}
				switch(strtoupper($src_encoding.'_'.$dest_encoding))
				{
					case 'ISO-8859-1_':
					case 'ISO-8859-1_US-ASCII':
						$escaped_data = str_replace(array('&', '"', "'", '<', '>'), array('&amp;', '&quot;', '&apos;', '&lt;', '&gt;'), $data);
						$escaped_data = str_replace($GLOBALS['xml_iso88591_Entities']['in'], $GLOBALS['xml_iso88591_Entities']['out'], $escaped_data);
						break;
					case 'ISO-8859-1_UTF-8':
						$escaped_data = str_replace(array('&', '"', "'", '<', '>'), array('&amp;', '&quot;', '&apos;', '&lt;', '&gt;'), $data);
						$escaped_data = utf8_encode($escaped_data);
						break;
					case 'ISO-8859-1_ISO-8859-1':
					case 'US-ASCII_US-ASCII':
					case 'US-ASCII_UTF-8':
					case 'US-ASCII_':
					case 'US-ASCII_ISO-8859-1':
					case 'UTF-8_UTF-8':
						$escaped_data = str_replace(array('&', '"', "'", '<', '>'), array('&amp;', '&quot;', '&apos;', '&lt;', '&gt;'), $data);
						break;
					case 'UTF-8_':
					case 'UTF-8_US-ASCII':
					case 'UTF-8_ISO-8859-1':
	// NB: this will choke on invalid UTF-8, going most likely beyond EOF
	$escaped_data = "";
	// be kind to users creating string xmlrpcvals out of different php types
	$data = (string) $data;
	$ns = strlen ($data);
	for ($nn = 0; $nn < $ns; $nn++)
	{
		$ch = $data[$nn];
		$ii = ord($ch);
//1 7 0bbbbbbb (127)
		if ($ii < 128)
		{
			/// @todo shall we replace this with a (suuposedly) faster str_replace?
			switch($ii){
				case 34:
					$escaped_data .= '&quot;';
					break;
				case 38:
					$escaped_data .= '&amp;';
				case 39:
					$escaped_data .= '&apos;';
					break;
				case 60:
					$escaped_data .= '&lt;';
					break;
				case 62:
					$escaped_data .= '&gt;';
					break;
				default:
					$escaped_data .= $ch;
			} // switch
		}
//2 11 110bbbbb 10bbbbbb (2047)
		else if ($ii>>5 == 6)
		{
			$b1 = ($ii & 31);
			$ii = ord($data[$nn+1]);
			$b2 = ($ii & 63);
			$ii = ($b1 * 64) + $b2;
			$ent = sprintf ("&#%d;", $ii);
			$escaped_data .= $ent;
		}
//3 16 1110bbbb 10bbbbbb 10bbbbbb
		else if ($ii>>4 == 14)
		{
			$b1 = ($ii & 31);
			$ii = ord($data[$nn+1]);
			$b2 = ($ii & 63);
			$ii = ord($data[$nn+2]);
			$b3 = ($ii & 63);
			$ii = ((($b1 * 64) + $b2) * 64) + $b3;
			$ent = sprintf ("&#%d;", $ii);
			$escaped_data .= $ent;
		}
//4 21 11110bbb 10bbbbbb 10bbbbbb 10bbbbbb
		else if ($ii>>3 == 30)
		{
			$b1 = ($ii & 31);
			$ii = ord($data[$nn+1]);
			$b2 = ($ii & 63);
			$ii = ord($data[$nn+2]);
			$b3 = ($ii & 63);
			$ii = ord($data[$nn+3]);
			$b4 = ($ii & 63);
			$ii = ((((($b1 * 64) + $b2) * 64) + $b3) * 64) + $b4;
			$ent = sprintf ("&#%d;", $ii);
			$escaped_data .= $ent;
		}
	}
						break;
					default:
						$escaped_data = '';
						error_log("Converting from $src_encoding to $dest_encoding: not supported...");
				}
//		} // switch
		return $escaped_data;
	}

	function xmlrpc_se($parser, $name, $attrs)
	{
		// if invalid xmlrpc already detected, skip all processing
		if ($GLOBALS['_xh']['isf'] < 2)
		{
			// check for correct element nesting
			// top level element can only be of 2 types
			if (count($GLOBALS['_xh']['stack']) == 0)
			{
				if ($name != 'METHODRESPONSE' && $name != 'METHODCALL')
				{
					$GLOBALS['_xh']['isf'] = 2;
					$GLOBALS['_xh']['isf_reason'] = 'missing top level xmlrpc element';
					return;
				}
			}
			else
			{
				// not top level element: see if parent is OK
				$parent = end($GLOBALS['_xh']['stack']);
				if (!array_key_exists($name, $GLOBALS['xmlrpc_valid_parents']) || !in_array($parent, $GLOBALS['xmlrpc_valid_parents'][$name]))
				{
					$GLOBALS['_xh']['isf'] = 2;
					$GLOBALS['_xh']['isf_reason'] = "xmlrpc element $name cannot be child of $parent";
					return;
				}
			}

			switch($name)
			{
				case 'STRUCT':
				case 'ARRAY':
					// create an empty array to hold child values, and push it onto appropriate stack
					$cur_val = array();
					$cur_val['values'] = array();
					$cur_val['type'] = $name;
					// check for out-of-band information to rebuild php objs
					// and in case it is found, save it
					if (@isset($attrs['PHP_CLASS']))
					{
						$cur_val['php_class'] = $attrs['PHP_CLASS'];
					}
					$GLOBALS['_xh']['valuestack'][] = $cur_val;
					break;
				case 'DATA':
				case 'METHODCALL':
				case 'METHODRESPONSE':
				case 'PARAMS':
					// valid elements that add little to processing
					break;
				case 'METHODNAME':
				case 'NAME':
					$GLOBALS['_xh']['ac']='';
					break;
				case 'FAULT':
					$GLOBALS['_xh']['isf']=1;
					break;
				case 'VALUE':
					$GLOBALS['_xh']['vt']='value'; // indicator: no value found yet
					$GLOBALS['_xh']['ac']='';
					$GLOBALS['_xh']['lv']=1;
					$GLOBALS['_xh']['php_class']=null;
					break;
				case 'I4':
				case 'INT':
				case 'STRING':
				case 'BOOLEAN':
				case 'DOUBLE':
				case 'DATETIME.ISO8601':
				case 'BASE64':
					if ($GLOBALS['_xh']['vt']!='value')
					{
						//two data elements inside a value: an error occurred!
						$GLOBALS['_xh']['isf'] = 2;
						$GLOBALS['_xh']['isf_reason'] = "$name element following a {$GLOBALS['_xh']['vt']} element inside a single value";
						return;
					}

					$GLOBALS['_xh']['ac']=''; // reset the accumulator
					break;
				case 'MEMBER':
					$GLOBALS['_xh']['valuestack'][count($GLOBALS['_xh']['valuestack'])-1]['name']=''; // set member name to null, in case we do not find in the xml later on
					//$GLOBALS['_xh']['ac']='';
					// Drop trough intentionally
				case 'PARAM':
					// clear value type, so we can check later if no value has been passed for this param/member
					$GLOBALS['_xh']['vt']=null;
					break;
				default:
					/// INVALID ELEMENT: RAISE ISF so that it is later recognized!!!
					$GLOBALS['_xh']['isf'] = 2;
					$GLOBALS['_xh']['isf_reason'] = "found not-xmlrpc xml element $name";
					break;
			}

			// Save current element name to stack, to validate nesting
			$GLOBALS['_xh']['stack'][] = $name;

			if($name!='VALUE')
			{
				$GLOBALS['_xh']['lv']=0;
			}
		}
	}

	function xmlrpc_ee($parser, $name, $rebuild_xmlrpcvals = true)
	{
		if ($GLOBALS['_xh']['isf'] < 2)
		{
			// push this element name from stack
			// NB: if XML validates, correct opening/closing is guaranteed and
			// we do not have to check for $name == $curr_elem.
			// we also checked for proper nesting at start of elements...
			$curr_elem = array_pop($GLOBALS['_xh']['stack']);

			switch($name)
			{
				case 'STRUCT':
				case 'ARRAY':
					// fetch out of stack array of values, and promote it to current value
					$curr_val = array_pop($GLOBALS['_xh']['valuestack']);
					$GLOBALS['_xh']['value'] = $curr_val['values'];
					$GLOBALS['_xh']['vt']=strtolower($name);
					if (isset($curr_val['php_class']))
					{
						$GLOBALS['_xh']['php_class'] = $curr_val['php_class'];
					}
					break;
				case 'NAME':
					$GLOBALS['_xh']['valuestack'][count($GLOBALS['_xh']['valuestack'])-1]['name'] = $GLOBALS['_xh']['ac'];
					break;
				case 'BOOLEAN':
				case 'I4':
				case 'INT':
				case 'STRING':
				case 'DOUBLE':
				case 'DATETIME.ISO8601':
				case 'BASE64':
					$GLOBALS['_xh']['vt']=strtolower($name);
					if ($name=='STRING')
					{
						$GLOBALS['_xh']['value']=$GLOBALS['_xh']['ac'];
					}
					elseif ($name=='DATETIME.ISO8601')
					{
						/// @todo validate datetime values with a correct format mask?
						$GLOBALS['_xh']['vt']=$GLOBALS['xmlrpcDateTime'];
						$GLOBALS['_xh']['value']=$GLOBALS['_xh']['ac'];
					}
					elseif ($name=='BASE64')
					{
						/// @todo check for failure of base64 decoding / catch warnings
						$GLOBALS['_xh']['value']=base64_decode($GLOBALS['_xh']['ac']);
					}
					elseif ($name=='BOOLEAN')
					{
						// special case here: we translate boolean 1 or 0 into PHP
							// constants true or false
							// NB: this simple checks helps a lot sanitizing input, ie no
							// security problems around here
							if ($GLOBALS['_xh']['ac']=='1')
							{
								$GLOBALS['_xh']['value']=true;
							}
							else
							{
								// log if receiveing something strange, even though we set the value to false anyway
								if ($GLOBALS['_xh']['ac']!='0')
									error_log('XML-RPC: invalid value received in BOOLEAN: '.$GLOBALS['_xh']['ac']);
								$GLOBALS['_xh']['value']=false;
							}
					}
					elseif ($name=='DOUBLE')
					{
						// we have a DOUBLE
						// we must check that only 0123456789-.<space> are characters here
						if (!ereg("^[+-]?[eE0123456789 \\t.]+$", $GLOBALS['_xh']['ac']))
						{
							/// @todo: find a better way of throwing an error
							// than this!
							error_log('XML-RPC: non numeric value received in DOUBLE: '.$GLOBALS['_xh']['ac']);
							$GLOBALS['_xh']['value']='ERROR_NON_NUMERIC_FOUND';
						}
						else
						{
							// it's ok, add it on
							$GLOBALS['_xh']['value']=(double)$GLOBALS['_xh']['ac'];
						}
					}
					else
					{
						// we have an I4/INT
						// we must check that only 0123456789-<space> are characters here
						if (!ereg("^[+-]?[0123456789 \\t]+$", $GLOBALS['_xh']['ac']))
						{
							/// @todo find a better way of throwing an error
							// than this!
							error_log('XML-RPC: non numeric value received in INT: '.$GLOBALS['_xh']['ac']);
							$GLOBALS['_xh']['value']='ERROR_NON_NUMERIC_FOUND';
						}
						else
						{
							// it's ok, add it on
							$GLOBALS['_xh']['value']=(int)$GLOBALS['_xh']['ac'];
						}
					}
					$GLOBALS['_xh']['ac']=''; // is this necessary?
					$GLOBALS['_xh']['lv']=3; // indicate we've found a value
					break;
				case 'VALUE':
					// This if() detects if no scalar was inside <VALUE></VALUE>
					if ($GLOBALS['_xh']['vt']=='value')
					{
						$GLOBALS['_xh']['value']=$GLOBALS['_xh']['ac'];
						$GLOBALS['_xh']['vt']=$GLOBALS['xmlrpcString'];
					}

					if ($rebuild_xmlrpcvals)
					{
						// build the xmlrpc val out of the data received, and substitute it
						$temp =& new xmlrpcval($GLOBALS['_xh']['value'], $GLOBALS['_xh']['vt']);
						// in case we got info about underlying php class, save it
						// in the object we're rebuilding
						if (isset($GLOBALS['_xh']['php_class']))
							$temp->_php_class = $GLOBALS['_xh']['php_class'];
						// check if we are inside an array or struct:
						// if value just built is inside an array, let's move it into array on the stack
						$vscount = count($GLOBALS['_xh']['valuestack']);
						if ($vscount && $GLOBALS['_xh']['valuestack'][$vscount-1]['type']=='ARRAY')
						{
							$GLOBALS['_xh']['valuestack'][$vscount-1]['values'][] = $temp;
						}
						else
						{
							$GLOBALS['_xh']['value'] = $temp;
						}
					}
					else
					{
						/// @todo this needs to treat correctly php-serialized objects,
						/// since std deserializing is done by php_xmlrpc_decode,
						/// which we will not be calling...
						if (isset($GLOBALS['_xh']['php_class']))
						{
						}

						// check if we are inside an array or struct:
						// if value just built is inside an array, let's move it into array on the stack
						$vscount = count($GLOBALS['_xh']['valuestack']);
						if ($vscount && $GLOBALS['_xh']['valuestack'][$vscount-1]['type']=='ARRAY')
						{
							$GLOBALS['_xh']['valuestack'][$vscount-1]['values'][] = $GLOBALS['_xh']['value'];
						}
					}
					break;
				case 'MEMBER':
					$GLOBALS['_xh']['ac']=''; // is this necessary?
					// add to array in the stack the last element built,
					// unless no VALUE was found
					if ($GLOBALS['_xh']['vt'])
					{
						$vscount = count($GLOBALS['_xh']['valuestack']);
						$GLOBALS['_xh']['valuestack'][$vscount-1]['values'][$GLOBALS['_xh']['valuestack'][$vscount-1]['name']] = $GLOBALS['_xh']['value'];
					} else
						error_log('XML-RPC: missing VALUE inside STRUCT in received xml');
					break;
				case 'DATA':
					$GLOBALS['_xh']['ac']=''; // is this necessary?
					break;
				case 'PARAM':
					// add to array of params the current value,
					// unless no VALUE was found
					if ($GLOBALS['_xh']['vt'])
					{
						$GLOBALS['_xh']['params'][]=$GLOBALS['_xh']['value'];
						$GLOBALS['_xh']['pt'][]=$GLOBALS['_xh']['vt'];
					}
					else
						error_log('XML-RPC: missing VALUE inside PARAM in received xml');
					break;
				case 'METHODNAME':
					$GLOBALS['_xh']['method']=ereg_replace("^[\n\r\t ]+", '', $GLOBALS['_xh']['ac']);
					break;
				case 'PARAMS':
				case 'FAULT':
				case 'METHODCALL':
				case 'METHORESPONSE':
					break;
				default:
					// End of INVALID ELEMENT!
					// shall we add an assert here for unreachable code???
					break;
			}
		}
	}

	function xmlrpc_ee_fast($parser, $name)
	{
		xmlrpc_ee($parser, $name, false);
	}

	function xmlrpc_cd($parser, $data)
	{
		//if(ereg("^[\n\r \t]+$", $data)) return;
		// print "adding [${data}]\n";

		// skip processing if xml fault already detected
		if ($GLOBALS['_xh']['isf'] < 2)
		{
			if($GLOBALS['_xh']['lv']!=3)
			{
				// "lookforvalue==3" means that we've found an entire value
				// and should discard any further character data
				if($GLOBALS['_xh']['lv']==1)
				{
					// if we've found text and we're just in a <value> then
					// say we've found a value
					$GLOBALS['_xh']['lv']=2;
				}
				if(!@isset($GLOBALS['_xh']['ac']))
				{
					$GLOBALS['_xh']['ac'] = '';
				}
				$GLOBALS['_xh']['ac'].=$data;
			}
		}
	}

	function xmlrpc_dh($parser, $data)
	{
		// skip processing if xml fault already detected
		if ($GLOBALS['_xh']['isf'] < 2)
		{
			if(substr($data, 0, 1) == '&' && substr($data, -1, 1) == ';')
			{
				if($GLOBALS['_xh']['lv']==1)
				{
					$GLOBALS['_xh']['lv']=2;
				}
				$GLOBALS['_xh']['ac'].=$data;
			}
		}
	}

	class xmlrpc_client
	{
		var $path;
		var $server;
		var $port=0;
		var $method='http';
		var $errno;
		var $errstr;
		var $debug=0;
		var $username='';
		var $password='';
		var $cert='';
		var $certpass='';
		var $key='';
		var $keypass='';
		var $verifypeer=1;
		var $verifyhost=1;
		var $no_multicall=false;
		var $proxy = '';
		var $proxyport=0;
		var $proxy_user = '';
		var $proxy_pass = '';
		var $cookies=array();
		/**
		* List of http compression methods accepted by the client for responses.
		* NB: PHP supports deflate, gzip compressions out of the box if compiled w. zlib
		*
		* NNB: you can set it to any non-empty array for HTTP11 and HTTPS, since
		* in those cases it will be up to CURL to decide the compression methods
		* it supports. You might check for the presence of 'zlib' in the output of
		* curl_version() to determine wheter compression is supported or not
		*/
		var $accepted_compression = array();
		/**
		* Name of compression scheme to be used for sending requests.
		* Either null, gzip or deflate
		*/
		var $request_compression = '';
		/**
		* CURL handle: used for keep-alive connections (PHP 4.3.8 up, see:
		* http://curl.haxx.se/docs/faq.html#7.3)
		*/
		var $xmlrpc_curl_handle = null;
		/// Wheter to use persistent connections for http 1.1 and https
		var $keepalive = false;
		/// Charset encodings that can be decoded without problems by the client
		var $accepted_charset_encodings = array();
		/// Charset encoding to be used in serializing request. NULL = use ASCII
		var $request_charset_encoding = '';
		/**
		* Decides the content of xmlrpcresp objects returned by calls to send()
		* valid strings are 'xmlrpcvals', 'phpvals' or 'xml'
		*/
		var $return_type = 'xmlrpcvals';

		/**
		* @param string $path either the complete server URL or the PATH part of the xmlrc server URL, e.g. /xmlrpc/server.php
		* @param string $server the server name / ip address
		* @param integer $port the port the server is listening on, defaults to 80 or 443 depending on protocol used
		* @param string $method the http protocol variant: defaults to 'http', 'https' and 'http11' can be used if CURL is installed
		*/
		function xmlrpc_client($path, $server='', $port='', $method='')
		{
			// allow user to specify all params in $path
			if($server == '' and $port == '' and $method == '')
			{
				$parts = parse_url($path);
				$server = $parts['host'];
				$path = $parts['path'];
				if(isset($parts['query']))
				{
					$path .= '?'.$parts['query'];
				}
				if(isset($parts['fragment']))
				{
					$path .= '#'.$parts['fragment'];
				}
				if(isset($parts['port']))
				{
					$port = $parts['port'];
				}
				if(isset($parts['scheme']))
				{
					$method = $parts['scheme'];
				}
				if(isset($parts['user']))
				{
					$this->username = $parts['user'];
				}
				if(isset($parts['pass']))
				{
					$this->password = $parts['pass'];
				}
			}
			if($path == '' || $path[0] != '/')
			{
				$this->path='/'.$path;
			}
			else
			{
				$this->path=$path;
			}
			$this->server=$server;
			if($port != '')
			{
				$this->port=$port;
			}
			if($method != '')
			{
				$this->method=$method;
			}

			// if ZLIB is enabled, let the client by default accept compressed responses
			if(function_exists('gzinflate') || (
				function_exists('curl_init') && (($info = curl_version()) &&
				((is_string($info) && strpos($info, 'zlib') !== null) || isset($info['libz_version'])))
			))
			{
				$this->accepted_compression = array('gzip', 'deflate');
			}

			// keepalives: enabled by default ONLY for PHP >= 4.3.8
			// (see http://curl.haxx.se/docs/faq.html#7.3)
			if(version_compare(phpversion(), '4.3.8') >= 0)
			{
				$this->keepalive = true;
			}

			// by default the xml parser can support these 3 charset encodings
			$this->accepted_charset_encodings = array('UTF-8', 'ISO-8859-1', 'US-ASCII');
		}

		/*
		* Enables/disables the echoing to screen of the xmlrpc responses received
		* @param integer $debug values 0, 1 and 2 are supported (2 = echo sent msg too, beside received response)
		* @access public
		*/
		function setDebug($in)
		{
			$this->debug=$in;
		}

		/*
		* Add some http BASIC AUTH credentials, used by the client to authenticate
		* @param string $u username
		* @param string $p password
		* @access public
		*/
		function setCredentials($u, $p)
		{
			$this->username=$u;
			$this->password=$p;
		}

		/*
		* Add a client-side https certificate
		* @param string $cert
		* @param string $certpass
		* @access public
		*/
		function setCertificate($cert, $certpass)
		{
			$this->cert = $cert;
			$this->certpass = $certpass;
		}

		/*
		* @param string $key     The name of a file containing a private SSL key
		* @param string $keypass The secret password needed to use the private SSL key
		* @access public
		* NB: does not work in older php/curl installs
		* Thanks to Daniel Convissor
		*/
		function setKey($key, $keypass)
		{
			$this->key = $key;
			$this->keypass = $keypass;
		}

		/*
		* @access public
		*/
		function setSSLVerifyPeer($i)
		{
			$this->verifypeer = $i;
		}

		/*
		* @access public
		*/
		function setSSLVerifyHost($i)
		{
			$this->verifyhost = $i;
		}

		/**
		* Set proxy info
		*
		* @param    string $proxyhost
		* @param    string $proxyport Defaults to 8080 for HTTP and 443 for HTTPS
		* @param    string $proxyusername Leave blank if proxy has public access
		* @param    string $proxypassword Leave blank if proxy has public access
		* @access   public
		*/
		function setProxy($proxyhost, $proxyport, $proxyusername = '', $proxypassword = '')
		{
			$this->proxy = $proxyhost;
			$this->proxyport = $proxyport;
			$this->proxy_user = $proxyusername;
			$this->proxy_pass = $proxypassword;
		}

		/**
		* Enables/disables reception of compressed xmlrpc responses.
		* Note that enabling reception of compressed responses merely adds some standard
		* http headers to xmlrpc requests. It is up to the xmlrpc server to return
		* compressed responses when receiving such requests.
		* @param string $compmethod either 'gzip', 'deflate', 'any' or ''
		* @access   public
		*/
		function setAcceptedCompression($compmethod)
		{
			if ($compmethod == 'any')
				$this->accepted_compression = array('gzip', 'deflate');
			else
				$this->accepted_compression = array($compmethod);
		}

		/**
		* Enables/disables http compression of xmlrpc request.
		* Take care when sending compressed requests: servers might not support them
		* (and automatic fallback to uncompressed requests is not yet implemented)
		* @param string $compmethod either 'gzip', 'deflate' or ''
		* @access   public
		*/
		function setRequestCompression($compmethod)
		{
			$this->request_compression = $compmethod;
		}

		/**
		* Adds a cookie to list of cookies that will be sent to server.
		* NB: setting any param but name and value will turn the cookie into a 'version 1' cookie:
		* do not do it unless you know what you are doing
		* @param string $name
		* @param string $value
		* @param string $path
		* @param string $domain
		* @param string $port
		* @access   public
		*
		* @todo check correctness of urlencoding cookie value (copied from php way of doing it...)
		*/
		function setCookie($name, $value='', $path='', $domain='', $port=null)
		{
			$this->cookies[$name]['value'] = urlencode($value);
			if ($path || $domain || $port)
			{
				$this->cookies[$name]['path'] = $path;
				$this->cookies[$name]['domain'] = $domain;
				$this->cookies[$name]['port'] = $port;
				$this->cookies[$name]['version'] = 1;
			}
			else
			{
				$this->cookies[$name]['version'] = 0;
			}
		}

		/**
		* Send an xmlrpc request
		* @param mixed $msg The message object, or an array of messages for using multicall, or the complete xml representation of a request
		* @param integer $timeout Connection timeout, in seconds, If unspecified, a platform specific timeout will apply
		* @param string $method if left unspecified, the http protocol chosen during creation of the object will be used
		*/
		function& send($msg, $timeout=0, $method='')
		{
			// if user deos not specify http protocol, use native method of this client
			// (i.e. method set during call to constructor)
			if($method == '')
			{
				$method = $this->method;
			}

			if(is_array($msg))
			{
				// $msg is an array of xmlrpcmsg's
				$r = $this->multicall($msg, $timeout, $method);
				return $r;
			}
			elseif(is_string($msg))
			{
				$n =& new xmlrpcmsg('');
				$n->payload = $msg;
				$msg = $n;
			}

			// where msg is an xmlrpcmsg
			$msg->debug=$this->debug;

			if($method == 'https')
			{
				$r =& $this->sendPayloadHTTPS(
					$msg,
					$this->server,
					$this->port,
					$timeout,
					$this->username,
					$this->password,
					$this->cert,
					$this->certpass,
					$this->proxy,
					$this->proxyport,
					$this->proxy_user,
					$this->proxy_pass,
					$this->keepalive,
					$this->key,
					$this->keypass
				);
			}
			elseif($method == 'http11')
			{
				$r =& $this->sendPayloadCURL(
					$msg,
					$this->server,
					$this->port,
					$timeout,
					$this->username,
					$this->password,
					null,
					null,
					$this->proxy,
					$this->proxyport,
					$this->proxy_user,
					$this->proxy_pass,
					'http',
					$this->keepalive
				);
			}
			else
			{
				$r =& $this->sendPayloadHTTP10(
					$msg,
					$this->server,
					$this->port,
					$timeout,
					$this->username,
					$this->password,
					$this->proxy,
					$this->proxyport,
					$this->proxy_user,
					$this->proxy_pass
				);
			}

			return $r;
		}

		/**
		* @access private
		*/
		function &sendPayloadHTTP10($msg, $server, $port, $timeout=0,$username='', $password='',
			$proxyhost='', $proxyport=0, $proxyusername='', $proxypassword='')
		{
			if($port==0)
			{
				$port=80;
			}

			// Only create the payload if it was not created previously
			if(empty($msg->payload))
			{
				$msg->createPayload($this->request_charset_encoding);
			}

			$payload = $msg->payload;
			// Deflate request body and set appropriate request headers
			if(function_exists('gzdeflate') && ($this->request_compression == 'gzip' || $this->request_compression == 'deflate'))
			{
				if($this->request_compression == 'gzip')
				{
					$a = @gzencode($msg->payload);
					if($a)
					{
						$payload = $a;
						$encoding_hdr = "Content-Encoding: gzip\r\n";
					}
				}
				else
				{
					$a = @gzdeflate($msg->payload);
					if($a)
					{
						$payload = $a;
						$encoding_hdr = "Content-Encoding: deflate\r\n";
					}
				}
			}
			else
			{
				$encoding_hdr = '';
			}

			// thanks to Grant Rauscher <grant7@firstworld.net>
			// for this
			$credentials='';
			if($username!='')
			{
				$credentials='Authorization: Basic ' . base64_encode($username . ':' . $password) . "\r\n";
			}

			$accepted_encoding = '';
			if(is_array($this->accepted_compression) && count($this->accepted_compression))
			{
				$accepted_encoding = 'Accept-Encoding: ' . implode(', ', $this->accepted_compression) . "\r\n";
			}

			$proxy_credentials = '';
			if($proxyhost)
			{
				if($proxyport == 0)
				{
					$proxyport = 8080;
				}
				$connectserver = $proxyhost;
				$connectport = $proxyport;
				$uri = 'http://'.$server.':'.$port.$this->path;
				if($proxyusername != '')
				{
					$proxy_credentials = 'Proxy-Authorization: Basic ' . base64_encode($proxyusername.':'.$proxypassword) . "\r\n";
				}
			}
			else
			{
				$connectserver = $server;
				$connectport = $port;
				$uri = $this->path;
			}

			// Cookie generation, as per rfc2965 (version 1 cookies) or
			// netscape's rules (version 0 cookies)
			$cookieheader='';
			foreach ($this->cookies as $name => $cookie)
			{
				if ($cookie['version'])
				{
					$cookieheader .= 'Cookie: $Version="' . $cookie['version'] . '"; ';
					$cookieheader .= $name . '="' . $cookie['value'] . '";';
					if ($cookie['path'])
						$cookieheader .= ' $Path="' . $cookie['path'] . '";';
					if ($cookie['domain'])
						$cookieheader .= ' $Domain="' . $cookie['domain'] . '";';
					if ($cookie['port'])
						$cookieheader .= ' $Port="' . $cookie['domain'] . '";';
					$cookieheader = substr($cookieheader, 0, -1) . "\r\n";
				}
				else
				{
					$cookieheader .= 'Cookie: ' . $name . '=' . $cookie['value'] . "\r\n";
				}
			}

			$op= "POST " . $uri. " HTTP/1.0\r\n" .
				"User-Agent: " . $GLOBALS['xmlrpcName'] . " " . $GLOBALS['xmlrpcVersion'] . "\r\n" .
				"Host: ". $server . "\r\n" .
				$credentials .
				$proxy_credentials .
				$accepted_encoding .
				$encoding_hdr .
				"Accept-Charset: " . implode(',', $this->accepted_charset_encodings) . "\r\n" .
				$cookieheader .
				"Content-Type: " . $msg->content_type . "\r\nContent-Length: " .
				strlen($payload) . "\r\n\r\n" .
				$payload;


			if($this->debug > 1)
			{
				print "<PRE>\n---SENDING---\n" . htmlentities($op) . "\n---END---\n</PRE>";
				// let the client see this now in case http times out...
				flush();
			}

			if($timeout>0)
			{
				$fp=@fsockopen($connectserver, $connectport, $this->errno, $this->errstr, $timeout);
			}
			else
			{
				$fp=@fsockopen($connectserver, $connectport, $this->errno, $this->errstr);
			}
			if($fp)
			{
				if($timeout>0 && function_exists('stream_set_timeout'))
				{
					stream_set_timeout($fp, $timeout);
				}
			}
			else
			{
				$this->errstr='Connect error: '.$this->errstr;
				$r=&new xmlrpcresp(0, $GLOBALS['xmlrpcerr']['http_error'], $this->errstr . ' (' . $this->errno . ')');
				return $r;
			}

			if(!fputs($fp, $op, strlen($op)))
			{
				$this->errstr='Write error';
				$r=&new xmlrpcresp(0, $GLOBALS['xmlrpcerr']['http_error'], $this->errstr);
				return $r;
			}
			else
			{
				// reset errno and errstr on succesful socket connection
				$this->errstr = '';
			}
			// G. Giunta 2005/10/24: close socket before parsing.
			// should yeld slightly better execution times, and make easier recursive calls (e.g. to follow http redirects)
			//$resp=&$msg->parseResponseFile($fp);
			$ipd='';
			while($data=fread($fp, 32768))
			{
				// shall we check for $data === FALSE?
				// as per the manual, it signals an error
				$ipd.=$data;
			}
			fclose($fp);
			$r =& $msg->parseResponse($ipd, false, $this->return_type);
			return $r;

		}

		/**
		* @access private
		*/
		function &sendPayloadHTTPS($msg, $server, $port, $timeout=0,$username='', $password='', $cert='',$certpass='',
			$proxyhost='', $proxyport=0, $proxyusername='', $proxypassword='', $keepalive=false, $key='', $keypass='')
		{
			$r =& $this->sendPayloadCURL($msg, $server, $port, $timeout, $username, $password, $cert, $certpass,
				$proxyhost, $proxyport, $proxyusername, $proxypassword, 'https', $keepalive, $key, $keypass);
			return $r;
		}

		/**
		* Contributed by Justin Miller <justin@voxel.net>
		* Requires curl to be built into PHP
		* NB: CURL versions before 7.11.10 cannot use proxy to talk to https servers!
		* @access private
		*/
		function &sendPayloadCURL($msg, $server, $port, $timeout=0, $username='', $password='', $cert='', $certpass='',
			$proxyhost='', $proxyport=0, $proxyusername='', $proxypassword='', $method='https', $keepalive=false,
			$key='', $keypass='')
		{
			if(!function_exists('curl_init'))
			{
				$this->errstr='CURL unavailable on this install';
				$r=&new xmlrpcresp(0, $GLOBALS['xmlrpcerr']['no_curl'], $GLOBALS['xmlrpcstr']['no_curl']);
				return $r;
			}
			if($method == 'https')
			{
				if(($info = curl_version()) &&
					((is_string($info) && strpos($info, 'OpenSSL') === null) || (is_array($info) && !isset($info['ssl_version']))))
				{
					$this->errstr='SSL unavailable on this install';
					$r=&new xmlrpcresp(0, $GLOBALS['xmlrpcerr']['no_ssl'], $GLOBALS['xmlrpcstr']['no_ssl']);
					return $r;
				}
			}

			if($port == 0)
			{
				if($method == 'http')
				{
					$port = 80;
				}
				else
				{
					$port = 443;
				}
			}

			// Only create the payload if it was not created previously
			if(empty($msg->payload))
			{
				$msg->createPayload($this->request_charset_encoding);
			}

			// Deflate request body and set appropriate request headers
			$payload = $msg->payload;
			if(function_exists('gzdeflate') && ($this->request_compression == 'gzip' || $this->request_compression == 'deflate'))
			{
				if($this->request_compression == 'gzip')
				{
					$a = @gzencode($msg->payload);
					if($a)
					{
						$payload = $a;
						$encoding_hdr = "Content-Encoding: gzip";
					}
				}
				else
				{
					$a = @gzdeflate($msg->payload);
					if($a)
					{
						$payload = $a;
						$encoding_hdr = "Content-Encoding: deflate";
					}
				}
			}
			else
			{
				$encoding_hdr = '';
			}

			if($this->debug > 1)
			{
				print "<PRE>\n---SENDING---\n" . htmlentities($payload) . "\n---END---\n</PRE>";
				// let the client see this now in case http times out...
				flush();
			}

			if(!$keepalive || !$this->xmlrpc_curl_handle)
			{
				$curl = curl_init($method . '://' . $server . ':' . $port . $this->path);
				if($keepalive)
				{
					$this->xmlrpc_curl_handle = $curl;
				}
			}
			else
			{
				$curl = $this->xmlrpc_curl_handle;
			}

			// results into variable
			curl_setopt($curl, CURLOPT_RETURNTRANSFER, 1);

			if($this->debug)
			{
				curl_setopt($curl, CURLOPT_VERBOSE, 1);
			}
			curl_setopt($curl, CURLOPT_USERAGENT, $GLOBALS['xmlrpcName'].' '.$GLOBALS['xmlrpcVersion']);
			// required for XMLRPC: post the data
			curl_setopt($curl, CURLOPT_POST, 1);
			// the data
			curl_setopt($curl, CURLOPT_POSTFIELDS, $payload);

			// return the header too
			curl_setopt($curl, CURLOPT_HEADER, 1);

			// will only work with PHP >= 5.0
			// NB: if we set an empty string, CURL will add http header indicating
			// ALL methods it is supporting. This is possibly a better option than
			// letting the user tell what curl can / cannot do...
			if(is_array($this->accepted_compression) && count($this->accepted_compression))
			{
				//curl_setopt($curl, CURLOPT_ENCODING, implode(',', $this->accepted_compression));
				// empty string means 'any supported by CURL' (shall we catch errors in case CURLOPT_SSLKEY undefined ?)
				curl_setopt($curl, CURLOPT_ENCODING, '');
			}
			// extra headers
			$headers = array('Content-Type: ' . $msg->content_type , 'Accept-Charset: ' . implode(',', $this->accepted_charset_encodings));
			// if no keepalive is wanted, let the server know it in advance
			if(!$keepalive)
			{
				$headers[] = 'Connection: close';
			}
			// request compression header
			if($encoding_hdr)
			{
				$headers[] = $encoding_hdr;
			}

			curl_setopt($curl, CURLOPT_HTTPHEADER, $headers);
			// timeout is borked
			if($timeout)
			{
				curl_setopt($curl, CURLOPT_TIMEOUT, $timeout == 1 ? 1 : $timeout - 1);
			}

			if($username && $password)
			{
				curl_setopt($curl, CURLOPT_USERPWD,"$username:$password");
			}

			if($method == 'https')
			{
				// set cert file
				if($cert)
				{
					curl_setopt($curl, CURLOPT_SSLCERT, $cert);
				}
				// set cert password
				if($certpass)
				{
					curl_setopt($curl, CURLOPT_SSLCERTPASSWD, $certpass);
				}
				// set key file (shall we catch errors in case CURLOPT_SSLKEY undefined ?)
				if($key)
				{
					curl_setopt($curl, CURLOPT_SSLKEY, $key);
				}
				// set key password (shall we catch errors in case CURLOPT_SSLKEY undefined ?)
				if($keypass)
				{
					curl_setopt($curl, CURLOPT_SSLKEYPASSWD, $keypass);
				}
				// whether to verify remote host's cert
				curl_setopt($curl, CURLOPT_SSL_VERIFYPEER, $this->verifypeer);
				// whether to verify cert's common name (CN); 0 for no, 1 to verify that it exists, and 2 to verify that it matches the hostname used
				curl_setopt($curl, CURLOPT_SSL_VERIFYHOST, $this->verifyhost);
			}

			// proxy info
			if($proxyhost)
			{
				if($proxyport == 0)
				{
					$proxyport = 8080; // NB: even for HTTPS, local connection is on port 8080
				}
				curl_setopt($curl, CURLOPT_PROXY,$proxyhost.':'.$proxyport);
				//curl_setopt($curl, CURLOPT_PROXYPORT,$proxyport);
				if($proxyusername)
				{
					curl_setopt($curl, CURLOPT_PROXYUSERPWD, $proxyusername.':'.$proxypassword);
				}
			}

			// NB: should we build cookie http headers by hand rather than let CURL do it?
			// the following code does not honour 'expires', 'path' and 'domain' cookie attributes
			// set to clint obj the the user...
			if (count($this->cookies))
			{
				$cookieheader = '';
				foreach ($this->cookies as $name => $cookie)
				{
					$cookieheader .= $name . '=' . $cookie['value'] . ', ';
				}
				curl_setopt($curl, CURLOPT_COOKIE, substr($cookieheader, 0, -2));
			}

			$result = curl_exec($curl);

			if(!$result)
			{
				$this->errstr='no response';
				$resp=&new xmlrpcresp(0, $GLOBALS['xmlrpcerr']['curl_fail'], $GLOBALS['xmlrpcstr']['curl_fail']. ': '. curl_error($curl));
				if(!$keepalive)
				{
					curl_close($curl);
				}
			}
			else
			{
				if(!$keepalive)
				{
					curl_close($curl);
				}
				$resp =& $msg->parseResponse($result, true, $this->return_type);
			}
			return $resp;
		}

		/**
		* Send an array of request messages and return an array of responses.
		* Unless $this->no_multicall has been set to true, it will try first
		* to use one single xmlrpc call to server method system.multicall, and
		* revert to sending many successive calls in case of failure.
		* This failure is also stored in $this->no_multicall for subsequent calls.
		* Unfortunately, there is no server error code universally used to denote
		* the fact that multicall is unsupported, so there is no way to reliably
		* distinguish between that and a temporary failure.
		* If you are sure that server supports multicall and do not want to
		* fallback to using many single calls, set the fourth parameter to FALSE.
		*
		* NB: trying to shoehorn extra functionality into existing syntax has resulted
		* in pretty much convoluted code...
		*
		* @access public
		* @param array $msgs an array of xmlrpcmsg objects
		* @param integer $timeout connection timeout (in seconds)
		* @param string $method the http protocol variant to be used
		* @param boolen fallback When true, upon receiveing an error during multicall, multiple single calls will be attempted
		*/
		function multicall($msgs, $timeout=0, $method='http', $fallback=true)
		{
			if(!$this->no_multicall)
			{
				$results = $this->_try_multicall($msgs, $timeout, $method);
				if(is_array($results))
				{
					// System.multicall succeeded
					return $results;
				}
				else
				{
					// either system.multicall is unsupported by server,
					// or call failed for some other reason.
					if ($fallback)
					{
						// Don't try it next time...
						$this->no_multicall = true;
					}
					else
					{
						if (is_a($result, 'xmlrpcresp'))
						{
							$result = $results;
						}
						else
						{
							$result =& new xmlrpcresp(0, $GLOBALS['xmlrpcerr']['multicall_error'], $GLOBALS['xmlrpcstr']['multicall_error']);
						}
					}
				}
			}
			else
			{
				// override fallback, in case careless user tries to do two
				// opposite things at the same time
				$fallback = true;
			}

			$results = array();
			if ($fallback)
			{
				// system.multicall is (probably) unsupported by server:
				// emulate multicall via multiple requests
				foreach($msgs as $msg)
				{
					$results[] =& $this->send($msg, $timeout, $method);
				}
			}
			else
			{
				// user does NOT want to fallback on many single calls:
				// since we should always return an array of responses,
				// return an array with the same error repeated n times
				foreach($msgs as $msg)
				{
					$results[] = $result;
				}
			}
			return $results;
		}

		/**
		* Attempt to boxcar $msgs via system.multicall.
		* Returns either an array of xmlrpcreponses, an xmlrpc error response
		* or false (when recived response does not respect valid multiccall syntax)
		* @access private
		*/
		function _try_multicall($msgs, $timeout, $method)
		{
			// Construct multicall message
			$calls = array();
			foreach($msgs as $msg)
			{
				$call['methodName'] =& new xmlrpcval($msg->method(),'string');
				$numParams = $msg->getNumParams();
				$params = array();
				for($i = 0; $i < $numParams; $i++)
				{
					$params[$i] = $msg->getParam($i);
				}
				$call['params'] =& new xmlrpcval($params, 'array');
				$calls[] =& new xmlrpcval($call, 'struct');
			}
			$multicall =& new xmlrpcmsg('system.multicall');
			$multicall->addParam(new xmlrpcval($calls, 'array'));

			// Attempt RPC call
			$result =& $this->send($multicall, $timeout, $method);
			//if(!is_object($result))
			//{
			//	return ($result || 0); // transport failed
			//}

			if($result->faultCode() != 0)
			{
				// call to system.multicall failed
				return $result;
			}

			// Unpack responses.
			$rets = $result->value();

			if ($this->return_type == 'xml')
			{
					return $rets;
			}
			else if ($this->return_type == 'phpvals')
			{
				///@todo test this code branch...
				$rets = $result->value();
				if(!is_array($rets))
				{
					return false;		// bad return type from system.multicall
				}
				$numRets = count($rets);
				if($numRets != count($msgs))
				{
					return false;		// wrong number of return values.
				}

				$response = array();
				for($i = 0; $i < $numRets; $i++)
				{
					$val = $rets[$i];
					if (!is_array($val)) {
						return false;
					}
					switch(count($val))
					{
						case 1:
							if(!isset($val[0]))
							{
								return false;		// Bad value
							}
							// Normal return value
							$response[$i] =& new xmlrpcresp($val[0], 0, '', 'phpvals');
							break;
						case 2:
							///	@todo remove usage of @: it is apparently quite slow
							$code = @$val['faultCode'];
							if(!is_int($code))
							{
								return false;
							}
							$str = @$val['faultString'];
							if(!is_string($str))
							{
								return false;
							}
							$response[$i] =& new xmlrpcresp(0, $code, $str);
							break;
						default:
							return false;
					}
				}
				return $response;
			}
			else // return type == 'xmlrpcvals'
			{
				$rets = $result->value();
				if($rets->kindOf() != 'array')
				{
					return false;		// bad return type from system.multicall
				}
				$numRets = $rets->arraysize();
				if($numRets != count($msgs))
				{
					return false;		// wrong number of return values.
				}

				$response = array();
				for($i = 0; $i < $numRets; $i++)
				{
					$val = $rets->arraymem($i);
					switch($val->kindOf())
					{
						case 'array':
							if($val->arraysize() != 1)
							{
								return false;		// Bad value
							}
							// Normal return value
							$response[$i] =& new xmlrpcresp($val->arraymem(0));
							break;
						case 'struct':
							$code = $val->structmem('faultCode');
							if($code->kindOf() != 'scalar' || $code->scalartyp() != 'int')
							{
								return false;
							}
							$str = $val->structmem('faultString');
							if($str->kindOf() != 'scalar' || $str->scalartyp() != 'string')
							{
								return false;
							}
							$response[$i] =& new xmlrpcresp(0, $code->scalarval(), $str->scalarval());
							break;
						default:
							return false;
					}
				}
				return $response;
			}
		}
	} // end class xmlrpc_client

	class xmlrpcresp
	{
		var $val = 0;
		var $valtyp;
		var $errno = 0;
		var $errstr = '';
		var $hdrs = array();
		var $_cookies = array();
		var $content_type = 'text/xml';

		/**
		* @param mixed  $val either an xmlrpcval obj, a php value or the xml serialization of an xmlrpcval (a string)
		* @param integer $fcode set it to anything but 0 to create an error response
		* @param string $fstr the error string, in case of an error response
		* @param string $valtyp either 'xmlrpcvals', 'phpvals' or 'xml'
		*
		* @todo add check that $val is of correct type???
		* NB: as of now we do not do it, since it might be either an xmlrpcval or a plain
		* php val, or a complete xml chunk, depending on usage of xmlrpc_client::send() inside which creator is called...
		*/
		function xmlrpcresp($val, $fcode = 0, $fstr = '', $valtyp='')
		{
			if($fcode != 0)
			{
				// error response
				$this->errno = $fcode;
				$this->errstr = $fstr;
				//$this->errstr = htmlspecialchars($fstr); // XXX: encoding probably shouldn't be done here; fix later.
			}
			/*elseif(!is_object($val) || !is_a($val, 'xmlrpcval'))
			{
				// programmer error
				error_log("Invalid type '" . gettype($val) . "' (value: $val) passed to xmlrpcresp. Defaulting to empty value.");
				$this->val =& new xmlrpcval();
			}*/
			else
			{
				// successful response
				$this->val = $val;
				if ($valtyp == '')
				{
					// user did not declare type of response value: try to guess it
					if (is_object($this->val) && is_a($this->val, 'xmlrpcval'))
					{
						$this->valtyp = 'xmlrpcvals';
					}
					else if (is_string($this->val))
					{
						$this->valtyp = 'xml';

					}
					else
					{
						$this->valtyp = 'phpvals';
					}
				}
				else
				{
					// user declares type of resp value: believe him
					$this->valtyp = $valtyp;
				}
			}
		}

		/*
		* @return integer the error code of this response (0 for not-error responses)
		*/
		function faultCode()
		{
			return $this->errno;
		}

		/*
		* @return string the error string of this response ('' for not-error responses)
		*/
		function faultString()
		{
			return $this->errstr;
		}

		/*
		* @return mixed the xmlrpcval object returned by the server. Might be an xml string or php value if the response has been created by specially configured xmlrpc_client objects
		*/
		function value()
		{
			return $this->val;
		}

		/**
		* Returns an array with the cookies received from the server.
		* Array has the form: $cookiename => array ('value' => $val, $attr1 => $val1, $attr2 = $val2, ...)
		* with attributes being e.g. 'expires', 'path', domain'.
		* NB: cookies sent as 'expired' by the server (i.e. with an expiry date in the past)
		* are still present in the array. It is up to the user-defined code to decide
		* how to use the received cookies, and wheter they have to be sent back with the next
		* request to the server (using xmlrpc_client::setCookie) or not
		* @return array array of cookies received from the server
		* @access public
		*/
		function cookies()
		{
			return $this->_cookies;
		}

		/**
		* Return xml representation of the response
		* @param string $charset_encoding the charset to be used for serialization. if null, US-ASCII is assumed
		* @return string the xml representation of the response
		*/
		function serialize($charset_encoding='')
		{
			if ($charset_encoding != '')
				$this->content_type = 'text/xml; charset=' . $charset_encoding;
			else
				$this->content_type = 'text/xml';
			$result = "<methodResponse>\n";
			if($this->errno)
			{
				// G. Giunta 2005/2/13: let non-ASCII response messages be tolerated by clients
				// by xml-encoding non ascii chars
				$result .= "<fault>\n" .
"<value>\n<struct><member><name>faultCode</name>\n<value><int>" . $this->errno .
"</int></value>\n</member>\n<member>\n<name>faultString</name>\n<value><string>" .
xmlrpc_encode_entitites($this->errstr, $GLOBALS['xmlrpc_internalencoding'], $charset_encoding) . "</string></value>\n</member>\n" .
"</struct>\n</value>\n</fault>";
			}
			else
			{
				if(!is_object($this->val) || !is_a($this->val, 'xmlrpcval'))
				{
					if (is_string($this->val) && $this->valtyp == 'xml')
					{
						$result .= "<params>\n<param>\n" .
							$this->val .
							"</param>\n</params>";
					}
					else
					{
						/// @todo try to build something serializable?
						die('cannot serialize xmlrpcresp objects whose content is native php values');
					}
				}
				else
				{
					$result .= "<params>\n<param>\n" .
						$this->val->serialize($charset_encoding) .
						"</param>\n</params>";
				}
			}
			$result .= "\n</methodResponse>";
			return $result;
		}
	}

	class xmlrpcmsg
	{
		var $payload;
		var $methodname;
		var $params=array();
		var $debug=0;
		var $content_type = 'text/xml';

		/*
		* @param string $meth the name of the method to invoke
		* @param array $pars array of parameters to be paased to the method (xmlrpcval objects)
		*/
		function xmlrpcmsg($meth, $pars=0)
		{
			$this->methodname=$meth;
			if(is_array($pars) && sizeof($pars)>0)
			{
				for($i=0; $i<sizeof($pars); $i++)
				{
					$this->addParam($pars[$i]);
				}
			}
		}

		function xml_header()
		{
			return "<?xml version=\"1.0\"?" . ">\n<methodCall>\n";
		}

		function xml_footer()
		{
			return "</methodCall>";
		}

		function kindOf()
		{
			return 'msg';
		}

		function createPayload($charset_encoding='')
		{
			if ($charset_encoding != '')
				$this->content_type = 'text/xml; charset=' . $charset_encoding;
			else
				$this->content_type = 'text/xml';
			$this->payload=$this->xml_header();
			$this->payload.='<methodName>' . $this->methodname . "</methodName>\n";
			//	if(sizeof($this->params)) {
			$this->payload.="<params>\n";
			for($i=0; $i<sizeof($this->params); $i++)
			{
				$p=$this->params[$i];
				$this->payload.="<param>\n" . $p->serialize($charset_encoding) .
				"</param>\n";
			}
			$this->payload.="</params>\n";
			// }
			$this->payload.=$this->xml_footer();
			//$this->payload=str_replace("\n", "\r\n", $this->payload);
		}

		/*
		* Gets/sets the xmlrpc method to be invoked
		* @param string $meth the method to be set (leave empty not to set it)
		* @return string the method that will be invoked
		* @access public
		*/
		function method($meth='')
		{
			if($meth!='')
			{
				$this->methodname=$meth;
			}
			return $this->methodname;
		}

		/*
		* @return string the xml representation of the message
		*/
		function serialize($charset_encoding='')
		{
			$this->createPayload($charset_encoding);
			return $this->payload;
		}

		/*
		* Add a parameter to the list of parameters to be used upon method invocation
		* @param xmlrpcval $par
		* @return boolean false on failure
		*/
		function addParam($par)
		{
			// add check: do not add to self params which are not xmlrpcvals
			if(is_object($par) && is_a($par, 'xmlrpcval'))
			{
				$this->params[]=$par;
				return true;
			}
			else
			{
				return false;
			}
		}

		/*
		* @param integer $i the index of the parameter to fetch (zero based)
		* @return xmlrpcval the i-th parameter
		*/
		function getParam($i) { return $this->params[$i]; }

		/*
		* @return integer the number of parameters currently set
		*/
		function getNumParams() { return sizeof($this->params); }

		/*
		* @access private
		* @todo add 2nd & 3rd param to be passed to ParseResponse() ???
		*/
		function &parseResponseFile($fp)
		{
			$ipd='';
			while($data=fread($fp, 32768))
			{
				$ipd.=$data;
			}
			//fclose($fp);
			$r =& $this->parseResponse($ipd);
			return $r;
		}

		/**
		* Parses HTTP headers and separates them from data.
		* @access private
		*/
		function &parseResponseHeaders(&$data, $headers_processed=false)
		{
				// Strip HTTP 1.1 100 Continue header if present
				while(ereg('^HTTP/1\.1 1[0-9]{2} ', $data))
				{
					$pos = strpos($data, 'HTTP', 12);
					// server sent a Continue header without any (valid) content following...
					// give the client a chance to know it
					if(!$pos && !is_int($pos)) // works fine in php 3, 4 and 5
					{
						break;
					}
					$data = substr($data, $pos);
				}
				if(!ereg('^HTTP/[0-9.]+ 200 ', $data))
				{
					$errstr= substr($data, 0, strpos($data, "\n")-1);
					error_log('XML-RPC: xmlrpcmsg::parseResponse: HTTP error, got response: ' .$errstr);
					$r=&new xmlrpcresp(0, $GLOBALS['xmlrpcerr']['http_error'], $GLOBALS['xmlrpcstr']['http_error']. ' (' . $errstr . ')');
					return $r;
				}

				$GLOBALS['_xh']['headers'] = array();
				$GLOBALS['_xh']['cookies'] = array();

				// be tolerant to usage of \n instead of \r\n to separate headers and data
				// (even though it is not valid http)
				$pos = strpos($data,"\r\n\r\n");
				if($pos || is_int($pos))
				{
					$bd = $pos+4;
				}
				else
				{
					$pos = strpos($data,"\n\n");
					if($pos || is_int($pos))
					{
						$bd = $pos+2;
					}
					else
					{
						// No separation between response headers and body: fault?
						$bd = 0;
					}
				}
				// be tolerant to line endings, and extra empty lines
				$ar = split("\r?\n", trim(substr($data, 0, $pos)));
				while(list(,$line) = @each($ar))
				{
					// take care of multi-line headers and cookies
					$arr = explode(':',$line,2);
					if(count($arr) > 1)
					{
						$header_name = strtolower(trim($arr[0]));
						/// @todo some other headers (the ones that allow a CSV list of values)
						/// do allow many values to be passed using multiple header lines.
						/// We should add content to $GLOBALS['_xh']['headers'][$header_name]
						/// instead of replacing it for those...
						if ($header_name == 'set-cookie' || $header_name == 'set-cookie2')
						{
							if ($header_name == 'set-cookie2')
							{
								// version 2 cookies:
								// there could be many cookies on one line, comma separated
								$cookies = explode(',', $arr[1]);
							}
							else
							{
								$cookies = array($arr[1]);
							}
							foreach ($cookies as $cookie)
							{
								// glue together all received cookies, using a comma to separate them
								// (same as php does with getallheaders())
								if (isset($GLOBALS['_xh']['headers'][$header_name]))
									$GLOBALS['_xh']['headers'][$header_name] .= ', ' . trim($cookie);
								else
									$GLOBALS['_xh']['headers'][$header_name] = trim($cookie);
								// parse cookie attributes, in case user wants to coorectly honour then
								// feature creep: only allow rfc-compliant cookie attributes?
								$cookie = explode(';', $cookie);
								foreach ($cookie as $pos => $val)
								{
									$val = explode('=', $val, 2);
									$tag = trim($val[0]);
									$val = trim(@$val[1]);
									/// @todo with version 1 cookies, we should strip leading and trailing " chars
									if ($pos == 0)
									{
										$cookiename = $tag;
										$GLOBALS['_xh']['cookies'][$tag] = array();
										$GLOBALS['_xh']['cookies'][$cookiename]['value'] = urldecode($val);
									}
									else
									{
										$GLOBALS['_xh']['cookies'][$cookiename][$tag] = $val;
									}
								}
							}
						}
						else
						{
							$GLOBALS['_xh']['headers'][$header_name] = trim($arr[1]);
						}
					}
					elseif(isset($header_name))
					{
						///	@todo version1 cookies might span multiple lines, thus breaking the parsing above
						$GLOBALS['_xh']['headers'][$header_name] .= ' ' . trim($line);
					}
				}
				// rebuild full cookie set
				/*if (isset($GLOBALS['_xh']['headers']['set-cookie']))
				{
					$cookies = array();
					$received = explode(';', $GLOBALS['_xh']['headers']['set-cookie']);
					foreach($received as $cookie)
					{
						list($name, $value) = explode('=', $cookie);
						$name = trim($name);
						$value = trim($value);
						// these values are in fact attributes
						if ($name != 'Comment' && $name != 'Comment' && $name != 'Comment' && $name != 'Comment' && $name != 'Comment' && $name != 'Comment')
						{
							$cookies[$name] = $value;
						}
					}
				}*/

				$data = substr($data, $bd);

				if($this->debug && count($GLOBALS['_xh']['headers']))
				{
					print '<PRE>';
					foreach($GLOBALS['_xh']['headers'] as $header => $value)
					{
						print "HEADER: $header: $value\n";
					}
					foreach($GLOBALS['_xh']['cookies'] as $header => $value)
					{
						print "COOKIE: $header={$value['value']}\n";
					}
					print "</PRE>\n";
				}

				// if CURL was used for the call, http headers have been processed,
				// and dechunking + reinflating have been carried out
				if(!$headers_processed)
				{
					// Decode chunked encoding sent by http 1.1 servers
					if(isset($GLOBALS['_xh']['headers']['transfer-encoding']) && $GLOBALS['_xh']['headers']['transfer-encoding'] == 'chunked')
					{
						if(!$data = decode_chunked($data))
						{
							error_log('XML-RPC: xmlrpcmsg::parseResponse: errors occurred when trying to rebuild the chunked data received from server');
							$r =& new xmlrpcresp(0, $GLOBALS['xmlrpcerr']['dechunk_fail'], $GLOBALS['xmlrpcstr']['dechunk_fail']);
							return $r;
						}
					}

					// Decode gzip-compressed stuff
					// code shamelessly inspired from nusoap library by Dietrich Ayala
					if(isset($GLOBALS['_xh']['headers']['content-encoding']))
					{
						if($GLOBALS['_xh']['headers']['content-encoding'] == 'deflate' || $GLOBALS['_xh']['headers']['content-encoding'] == 'gzip')
						{
							// if decoding works, use it. else assume data wasn't gzencoded
							if(function_exists('gzinflate'))
							{
								if($GLOBALS['_xh']['headers']['content-encoding'] == 'deflate' && $degzdata = @gzinflate($data))
								{
									$data = $degzdata;
									if($this->debug)
									print "<PRE>---INFLATED RESPONSE---[".strlen($data)." chars]---\n" . htmlentities($data) . "\n---END---</PRE>";
								}
								elseif($GLOBALS['_xh']['headers']['content-encoding'] == 'gzip' && $degzdata = @gzinflate(substr($data, 10)))
								{
									$data = $degzdata;
									if($this->debug)
									print "<PRE>---INFLATED RESPONSE---[".strlen($data)." chars]---\n" . htmlentities($data) . "\n---END---</PRE>";
								}
								else
								{
									error_log('XML-RPC: xmlrpcmsg::parseResponse: errors occurred when trying to decode the deflated data received from server');
									$r =& new xmlrpcresp(0, $GLOBALS['xmlrpcerr']['decompress_fail'], $GLOBALS['xmlrpcstr']['decompress_fail']);
									return $r;
								}
							}
							else
							{
								error_log('XML-RPC: xmlrpcmsg::parseResponse: the server sent deflated data. Your php install must have the Zlib extension compiled in to support this.');
								$r =& new xmlrpcresp(0, $GLOBALS['xmlrpcerr']['cannot_decompress'], $GLOBALS['xmlrpcstr']['cannot_decompress']);
								return $r;
							}
						}
					}
				} // end of 'if needed, de-chunk, re-inflate response'

				// real stupid hack to avoid PHP 4 complaining about returning NULL by ref
				$r = null;
				$r =& $r;
				return $r;
		}

		/*
		* @param string $data the xmlrpc response, eventually including http headers
		* @param bool   $headers_processed when true prevents parsing HTTP headers for interpretation of content-encoding and conseuqent decoding
		* @param string $return_type decides return type, i.e. content of response->value(). Either 'xmlrpcvals', 'xml' or 'phpvals'
		* @access private
		*/
		function &parseResponse($data='', $headers_processed=false, $return_type='xmlrpcvals')
		{
			//$hdrfnd = 0;
			if($this->debug)
			{
				//by maHo, replaced htmlspecialchars with htmlentities
				print "<PRE>---GOT---\n" . htmlentities($data) . "\n---END---\n</PRE>";
				$start = strpos($data, '<!-- SERVER DEBUG INFO (BASE64 ENCODED):');
				if ($start)
				{
					$start += strlen('<!-- SERVER DEBUG INFO (BASE64 ENCODED):');
					$end = strpos($data, '-->', $start);
					$comments = substr($data, $start, $end-$start);
					print "<PRE>---SERVER DEBUG INFO (DECODED) ---\n\t".htmlentities(str_replace("\n", "\n\t", base64_decode($comments)))."\n---END---\n</PRE>";
				}
			}

			if($data == '')
			{
				error_log('XML-RPC: xmlrpcmsg::parseResponse: no response received from server.');
				$r =& new xmlrpcresp(0, $GLOBALS['xmlrpcerr']['no_data'], $GLOBALS['xmlrpcstr']['no_data']);
				return $r;
			}

			$GLOBALS['_xh']=array();

			// parse the HTTP headers of the response, if present, and separate them from data
			if(ereg("^HTTP",$data))
			{
				$r =& $this->parseResponseHeaders($data, $headers_processed);
				if ($r)
				{
					return $r;
				}
			}
			else
			{
				$GLOBALS['_xh']['headers'] = array();
				$GLOBALS['_xh']['cookies'] = array();
			}


			// be tolerant of extra whitespace in response body
			$data = trim($data);

			/// @todo return an error msg if $data=='' ?

			// be tolerant of junk after methodResponse (e.g. javascript ads automatically inserted by free hosts)
			// idea from Luca Mariano <luca.mariano@email.it> originally in PEARified version of the lib
			$bd = false;
			// Poor man's version of strrpos for php 4...
			$pos = strpos($data, '</methodResponse>');
			while($pos || is_int($pos))
			{
				$bd = $pos+17;
				$pos = strpos($data, '</methodResponse>', $bd);
			}
			if($bd)
			{
				$data = substr($data, 0, $bd);
			}

			// if user wants back raw xml, give it to him
			if ($return_type == 'xml')
			{
				$r =& new xmlrpcresp($data, 0, '', 'xml');
				$r->hdrs = $GLOBALS['_xh']['headers'];
				$r->_cookies = $GLOBALS['_xh']['cookies'];
				return $r;
			}

			// try to 'guestimate' the character encoding of the received response
			$resp_encoding = guess_encoding(@$GLOBALS['_xh']['headers']['content-type'], $data);

			$GLOBALS['_xh']['stack'] = array();
			$GLOBALS['_xh']['valuestack'] = array();
			$GLOBALS['_xh']['isf']=0;
			$GLOBALS['_xh']['isf_reason']='';
			$GLOBALS['_xh']['ac']='';
			$GLOBALS['_xh']['qt']='';

			// if response charset encoding is not known / supported, try to use
			// the default encoding and parse the xml anyway, but log a warning...
			if (!in_array($resp_encoding, array('UTF-8', 'ISO-8859-1', 'US-ASCII')))
			// the following code might be better for mb_string enabled installs, but
			// makes the lib about 200% slower...
			//if (!is_valid_charset($resp_encoding, array('UTF-8', 'ISO-8859-1', 'US-ASCII')))
			{
				error_log('XML-RPC: xmlrpcmsg::parseResponse: invalid charset encoding of received response: '.$resp_encoding);
				$resp_encoding = $GLOBALS['xmlrpc_defencoding'];
			}
			$parser = xml_parser_create($resp_encoding);
			xml_parser_set_option($parser, XML_OPTION_CASE_FOLDING, true);
			// G. Giunta 2005/02/13: PHP internally uses ISO-8859-1, so we have to tell
			// the xml parser to give us back data in the expected charset
			xml_parser_set_option($parser, XML_OPTION_TARGET_ENCODING, $GLOBALS['xmlrpc_internalencoding']);

			if ($return_type == 'phpvals')
			{
				xml_set_element_handler($parser, 'xmlrpc_se', 'xmlrpc_ee_fast');
			}
			else
			{
				xml_set_element_handler($parser, 'xmlrpc_se', 'xmlrpc_ee');
			}

			xml_set_character_data_handler($parser, 'xmlrpc_cd');
			xml_set_default_handler($parser, 'xmlrpc_dh');

			if(!xml_parse($parser, $data, sizeof($data)))
			{
				// thanks to Peter Kocks <peter.kocks@baygate.com>
				if((xml_get_current_line_number($parser)) == 1)
				{
					$errstr = 'XML error at line 1, check URL';
				}
				else
				{
					$errstr = sprintf('XML error: %s at line %d',
						xml_error_string(xml_get_error_code($parser)),
						xml_get_current_line_number($parser));
				}
				error_log($errstr);
				$r=&new xmlrpcresp(0, $GLOBALS['xmlrpcerr']['invalid_return'], $GLOBALS['xmlrpcstr']['invalid_return'].' ('.$errstr.')');
				xml_parser_free($parser);
				if($this->debug)
				{
					print $errstr;
				}
				$r->hdrs = $GLOBALS['_xh']['headers'];
				$r->_cookies = $GLOBALS['_xh']['cookies'];
				return $r;
			}
			xml_parser_free($parser);
			if ($GLOBALS['_xh']['isf'] > 1)
			{
				if ($this->debug)
				{
					/// @todo echo something for user?
				}

				$r =& new xmlrpcresp(0, $GLOBALS['xmlrpcerr']['invalid_return'],
				$GLOBALS['xmlrpcstr']['invalid_return'] . ' ' . $GLOBALS['_xh']['isf_reason']);
			}
			elseif ($return_type == 'xmlrpcvals' && !is_object($GLOBALS['_xh']['value']))
			{
				// then something odd has happened
				// and it's time to generate a client side error
				// indicating something odd went on
				$r=&new xmlrpcresp(0, $GLOBALS['xmlrpcerr']['invalid_return'],
				$GLOBALS['xmlrpcstr']['invalid_return']);
			}
			else
			{
				if ($this->debug)
				{
					print "<PRE>---PARSED---\n" ;
					var_export($GLOBALS['_xh']['value']);
					print "\n---END---</PRE>";
				}				// note that using =& will raise an error if $GLOBALS['_xh']['st'] does not generate an object.

				$v =& $GLOBALS['_xh']['value'];

				if($GLOBALS['_xh']['isf'])
				{
					if ($return_type == 'xmlrpcvals')
					{
						$errno_v = $v->structmem('faultCode');
						$errstr_v = $v->structmem('faultString');
						$errno = $errno_v->scalarval();
						$errstr = $errstr_v->scalarval();
					}
					else
					{
						$errno = $v['faultCode'];
						$errstr = $v['faultString'];
					}

					if($errno == 0)
					{
						// FAULT returned, errno needs to reflect that
						$errno = -1;
					}

					$r =& new xmlrpcresp($v, $errno, $errstr);
				}
				else
				{
					$r=&new xmlrpcresp($v, 0, '', 'phpvals');
				}
			}

			$r->hdrs = $GLOBALS['_xh']['headers'];
			$r->_cookies = $GLOBALS['_xh']['cookies'];
			return $r;
		}
	}

	class xmlrpcval
	{
		var $me=array();
		var $mytype=0;
		var $_php_class=null;

		function xmlrpcval($val=-1, $type='')
		{
			//$this->me=array();
			//$this->mytype=0;
			if($val!==-1 || $type!='')
			{
				if($type=='')
				{
					$type='string';
				}
				if($GLOBALS['xmlrpcTypes'][$type]==1)
				{
					$this->addScalar($val,$type);
				}
				elseif($GLOBALS['xmlrpcTypes'][$type]==2)
				{
					$this->addArray($val);
				}
				elseif($GLOBALS['xmlrpcTypes'][$type]==3)
				{
					$this->addStruct($val);
				}
			}
		}

		function addScalar($val, $type='string')
		{
			$typeof=@$GLOBALS['xmlrpcTypes'][$type];
			if($typeof!=1)
			{
				error_log("XML-RPC: xmlrpcval::addScalar: not a scalar type ($typeof)");
				return 0;
			}

			// coerce booleans into correct values
			// NB: shall we do it for datetimes, integers and doubles, too?
			if($type==$GLOBALS['xmlrpcBoolean'])
			{
				if(strcasecmp($val,'true')==0 || $val==1 || ($val==true && strcasecmp($val,'false')))
				{
					$val=true;
				}
				else
				{
					$val=false;
				}
			}

			switch($this->mytype)
			{
				case 1:
					error_log('XML-RPC: xmlrpcval::addScalar: scalar xmlrpcval can have only one value');
					return 0;
				case 3:
					error_log('XML-RPC: xmlrpcval::addScalar: cannot add anonymous scalar to struct xmlrpcval');
					return 0;
				case 2:
					// we're adding a scalar value to an array here
					//$ar=$this->me['array'];
					//$ar[]=&new xmlrpcval($val, $type);
					//$this->me['array']=$ar;
					// Faster (?) avoid all the costly array-copy-by-val done here...
					$this->me['array'][]=&new xmlrpcval($val, $type);
					return 1;
				default:
					// a scalar, so set the value and remember we're scalar
					$this->me[$type]=$val;
					$this->mytype=$typeof;
					return 1;
			}
		}

		/// @todo add some checking for $vals to be an array of xmlrpcvals?
		function addArray($vals)
		{
			if($this->mytype==0)
			{
				$this->mytype=$GLOBALS['xmlrpcTypes']['array'];
				$this->me['array']=$vals;
				return 1;
			}
			elseif($this->mytype==2)
			{
				// we're adding to an array here
				$this->me['array'] = array_merge($this->me['array'], $vals);
			}
			else
			{
				error_log('XML-RPC: xmlrpcval::addArray: already initialized as a [' . $this->kindOf() . ']');
				return 0;
			}
		}

		/// @todo add some checking for $vals to be an array?
		function addStruct($vals)
		{
			if($this->mytype==0)
			{
				$this->mytype=$GLOBALS['xmlrpcTypes']['struct'];
				$this->me['struct']=$vals;
				return 1;
			}
			elseif($this->mytype==3)
			{
				// we're adding to a struct here
				$this->me['struct'] = array_merge($this->me['struct'], $vals);
			}
			else
			{
				error_log('XML-RPC: xmlrpcval::addStruct: already initialized as a [' . $this->kindOf() . ']');
				return 0;
			}
		}

		// poor man's version of print_r ???
		// DEPRECATED!
		function dump($ar)
		{
			foreach($ar as $key => $val)
			{
				echo "$key => $val<br />";
				if($key == 'array')
				{
					while(list($key2, $val2) = each($val))
					{
						echo "-- $key2 => $val2<br />";
					}
				}
			}
		}

		function kindOf()
		{
			switch($this->mytype)
			{
				case 3:
					return 'struct';
					break;
				case 2:
					return 'array';
					break;
				case 1:
					return 'scalar';
					break;
				default:
					return 'undef';
			}
		}

		function serializedata($typ, $val, $charset_encoding='')
		{
			$rs='';
			switch(@$GLOBALS['xmlrpcTypes'][$typ])
			{
				case 3:
					// struct
					if ($this->_php_class)
					{
						$rs.='<struct php_class="' . $this->_php_class . "\">\n";
					}
					else
					{
						$rs.="<struct>\n";
					}
					foreach($val as $key2 => $val2)
					{
						$rs.="<member><name>${key2}</name>\n";
						//$rs.=$this->serializeval($val2);
						$rs.=$val2->serialize();
						$rs.="</member>\n";
					}
					$rs.='</struct>';
					break;
				case 2:
					// array
					$rs.="<array>\n<data>\n";
					for($i=0; $i<sizeof($val); $i++)
					{
						//$rs.=$this->serializeval($val[$i]);
						$rs.=$val[$i]->serialize();
					}
					$rs.="</data>\n</array>";
					break;
				case 1:
					switch($typ)
					{
						case $GLOBALS['xmlrpcBase64']:
							$rs.="<${typ}>" . base64_encode($val) . "</${typ}>";
							break;
						case $GLOBALS['xmlrpcBoolean']:
							$rs.="<${typ}>" . ($val ? '1' : '0') . "</${typ}>";
							break;
						case $GLOBALS['xmlrpcString']:
							// G. Giunta 2005/2/13: do NOT use htmlentities, since
							// it will produce named html entities, which are invalid xml
							$rs.="<${typ}>" . xmlrpc_encode_entitites($val, $GLOBALS['xmlrpc_internalencoding'], $charset_encoding). "</${typ}>";
							// $rs.="<${typ}>" . htmlentities($val). "</${typ}>";
							break;
						case $GLOBALS['xmlrpcInt']:
						case $GLOBALS['xmlrpcI4']:
							$rs.="<${typ}>".(int)$val."</${typ}>";
							break;
						case $GLOBALS['xmlrpcDouble']:
							$rs.="<${typ}>".(double)$val."</${typ}>";
							break;
						default:
							// no standard type value should arrive here, but provide a possibility
							// for xmlrpcvals of unknown type...
							$rs.="<${typ}>${val}</${typ}>";
					}
					break;
				default:
					break;
			}
			return $rs;
		}

		/**
		* Return xml representation of the value
		* @param string $charset_encoding the charset to be used for serialization. if null, US-ASCII is assumed
		*/
		function serialize($charset_encoding='')
		{
			// add check? slower, but helps to avoid recursion in serializing broken xmlrpcvals...
			//if (is_object($o) && (get_class($o) == 'xmlrpcval' || is_subclass_of($o, 'xmlrpcval')))
			//{
				reset($this->me);
				list($typ, $val) = each($this->me);
				return '<value>' . $this->serializedata($typ, $val, $charset_encoding) . "</value>\n";
			//}
		}

		// DEPRECATED
		function serializeval($o)
		{
			// add check? slower, but helps to avoid recursion in serializing broken xmlrpcvals...
			//if (is_object($o) && (get_class($o) == 'xmlrpcval' || is_subclass_of($o, 'xmlrpcval')))
			//{
				$ar=$o->me;
				reset($ar);
				list($typ, $val) = each($ar);
				return '<value>' . $this->serializedata($typ, $val) . "</value>\n";
			//}
		}

		/**
		* Checks wheter a struct member with a given name is present.
		* Works only on xmlrpcvals of type struct.
		* @param string $m the name of the struct member to be looked up
		* @return boolean
		*/
		function structmemexists($m)
		{
			return array_key_exists($this->me['struct'][$m]);
		}

		/*
		* Returns the value of a given struct member (an xmlrpcval object in itself).
		* Will raise a php warning if struct member of given name does not exist
		* @param string $m the name of the struct member to be looked up
		* @return xmlrpcval
		*/
		function structmem($m)
		{
			return $this->me['struct'][$m];
		}

		function structreset()
		{
			reset($this->me['struct']);
		}

		function structeach()
		{
			return each($this->me['struct']);
		}

		// DEPRECATED! this code looks like it is very fragile and has not been fixed
		// for a long long time. Shall we remove it for 2.0?
		function getval()
		{
			// UNSTABLE
			reset($this->me);
			list($a,$b)=each($this->me);
			// contributed by I Sofer, 2001-03-24
			// add support for nested arrays to scalarval
			// i've created a new method here, so as to
			// preserve back compatibility

			if(is_array($b))
			{
				@reset($b);
				while(list($id,$cont) = @each($b))
				{
					$b[$id] = $cont->scalarval();
				}
			}

			// add support for structures directly encoding php objects
			if(is_object($b))
			{
				$t = get_object_vars($b);
				@reset($t);
				while(list($id,$cont) = @each($t))
				{
					$t[$id] = $cont->scalarval();
				}
				@reset($t);
				while(list($id,$cont) = @each($t))
				{
					//@eval('$b->'.$id.' = $cont;');
					@$b->$id = $cont;
				}
			}
			// end contrib
			return $b;
		}

		/**
		* Returns the value of a scalar xmlrpcval
		* @return mixed
		*/
		function scalarval()
		{
			reset($this->me);
			list(,$b)=each($this->me);
			return $b;
		}

		/**
		* Returns the type of the xmlrpcval.
		* For integers, 'int' is always returned in place of 'i4'
		* @return string
		*/
		function scalartyp()
		{
			reset($this->me);
			list($a,$b)=each($this->me);
			if($a==$GLOBALS['xmlrpcI4'])
			{
				$a=$GLOBALS['xmlrpcInt'];
			}
			return $a;
		}

		/**
		* Returns the m-th member of an xmlrpcval of struct type
		* @param integer $m the index of the value to be retrieved (zero based)
		* @return xmlrpcval
		*/
		function arraymem($m)
		{
			return $this->me['array'][$m];
		}

		/**
		* Returns the number of members in an xmlrpcval of array type
		* @return integer
		*/
		function arraysize()
		{
			return count($this->me['array']);
		}

		/**
		* Returns the number of members in an xmlrpcval of struct type
		* @return integer
		*/
		function structsize()
		{
			return count($this->me['struct']);
		}
	}


	// date helpers
	function iso8601_encode($timet, $utc=0)
	{
		// return an ISO8601 encoded string
		// really, timezones ought to be supported
		// but the XML-RPC spec says:
		//
		// "Don't assume a timezone. It should be specified by the server in its
		// documentation what assumptions it makes about timezones."
		//
		// these routines always assume localtime unless
		// $utc is set to 1, in which case UTC is assumed
		// and an adjustment for locale is made when encoding
		if(!$utc)
		{
			$t=strftime("%Y%m%dT%H:%M:%S", $timet);
		}
		else
		{
			if(function_exists('gmstrftime'))
			{
				// gmstrftime doesn't exist in some versions
				// of PHP
				$t=gmstrftime("%Y%m%dT%H:%M:%S", $timet);
			}
			else
			{
				$t=strftime("%Y%m%dT%H:%M:%S", $timet-date('Z'));
			}
		}
		return $t;
	}

	function iso8601_decode($idate, $utc=0)
	{
		// return a timet in the localtime, or UTC
		$t=0;
		if(ereg("([0-9]{4})([0-9]{2})([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})", $idate, $regs))
		{
			if($utc)
			{
				$t=gmmktime($regs[4], $regs[5], $regs[6], $regs[2], $regs[3], $regs[1]);
			}
			else
			{
				$t=mktime($regs[4], $regs[5], $regs[6], $regs[2], $regs[3], $regs[1]);
			}
		}
		return $t;
	}

	/**
	* Takes an xmlrpc value in PHP xmlrpcval object format
	* and translates it into native PHP types.
	* Works with xmlrpc message objects as input, too.
	*
	* @author Dan Libby (dan@libby.com)
	*
	* @param  xmlrpcval $xmlrpc_val
	* @param  array     $options    if 'decode_php_objs' is set in the options array, xmlrpc structs can be decoded into php objects
	* @return mixed
	*/
	function php_xmlrpc_decode($xmlrpc_val, $options=array())
	{
		switch($xmlrpc_val->kindOf())
		{
			case 'scalar':
				return $xmlrpc_val->scalarval();
			case 'array':
				$size = $xmlrpc_val->arraysize();
				$arr = array();
				for($i = 0; $i < $size; $i++)
				{
					$arr[] = php_xmlrpc_decode($xmlrpc_val->arraymem($i), $options);
				}
				return $arr;
			case 'struct':
				$xmlrpc_val->structreset();
				// If user said so, try to rebuild php objects for specific struct vals.
				/// @todo should we raise a warning for class not found?
				// shall we check for proper subclass of xmlrpcval instead of
				// presence of _php_class to detect what we can do?
				if (in_array('decode_php_objs', $options) && $xmlrpc_val->_php_class != ''
					&& class_exists($xmlrpc_val->_php_class))
				{
					$obj = @new $xmlrpc_val->_php_class;
					while(list($key,$value)=$xmlrpc_val->structeach())
					{
						$obj->$key = php_xmlrpc_decode($value, $options);
					}
					return $obj;
				}
				else
				{
					$arr = array();
					while(list($key,$value)=$xmlrpc_val->structeach())
					{
						$arr[$key] = php_xmlrpc_decode($value, $options);
					}
					return $arr;
				}
			case 'msg':
				$paramcount = $xmlrpc_val->getNumParams();
				$arr = array();
				for($i = 0; $i < $paramcount; $i++)
				{
					$arr[] = php_xmlrpc_decode($xmlrpc_val->getParam($i));
				}
				return $arr;
			}
	}

	if(function_exists('xmlrpc_decode'))
	{
		define('XMLRPC_EPI_ENABLED','1');
	}
	else
	{
		define('XMLRPC_EPI_ENABLED','0');
	}

	/**
	* Takes native php types and encodes them into xmlrpc PHP object format.
	* It will not re-encode xmlrpcval objects.
	* Feature creep -- could support more types via optional type argument
	* (string => datetime support has been added, ??? => base64 not yet)
	*
	* @author Dan Libby (dan@libby.com)
	*
	* @param mixed $php_val the value to be converted into an xmlrpcval object
	* @param array $options	can include 'encode_php_objs' and 'auto_dates'
	* @return xmlrpcval
	*/
	function &php_xmlrpc_encode($php_val, $options=array())
	{
		$type = gettype($php_val);
		$xmlrpc_val =& new xmlrpcval;

		switch($type)
		{
			case 'array':
				// PHP arrays can be encoded to either xmlrpc structs or arrays,
				// depending on wheter they are hashes or plain 0..n integer indexed
				// A shorter one-liner would be
				// $tmp = array_diff(array_keys($php_val), range(0, count($php_val)-1));
				// but execution time skyrockets!
				$j = 0;
				$arr = array();
				$ko = false;
				foreach($php_val as $key => $val)
				{
					$arr[$key] =& php_xmlrpc_encode($val, $options);
					if(!$ko && $key !== $j)
					{
						$ko = true;
					}
					$j++;
				}
				if($ko)
				{
					$xmlrpc_val->addStruct($arr);
				}
				else
				{
					$xmlrpc_val->addArray($arr);
				}
				break;
			case 'object':
				if(is_a($php_val, 'xmlrpcval'))
				{
					$xmlrpc_val = $php_val;
				}
				else
				{
					$arr = array();
					while(list($k,$v) = each($php_val))
					{
						$arr[$k] = php_xmlrpc_encode($v, $options);
					}
					$xmlrpc_val->addStruct($arr);
					if (in_array('encode_php_objs', $options))
					{
						// let's save original class name into xmlrpcval:
						// might be useful later on...
						$xmlrpc_val->_php_class = get_class($php_val);
					}
				}
				break;
			case 'integer':
				$xmlrpc_val->addScalar($php_val, $GLOBALS['xmlrpcInt']);
				break;
			case 'double':
				$xmlrpc_val->addScalar($php_val, $GLOBALS['xmlrpcDouble']);
				break;
			case 'string':
				if (in_array('auto_dates', $options) && ereg("^[0-9]{8}\T{1}[0-9]{2}\:[0-9]{2}\:[0-9]{2}$", $php_val))
					$xmlrpc_val->addScalar($php_val, $GLOBALS['xmlrpcDateTime']);
				else
					$xmlrpc_val->addScalar($php_val, $GLOBALS['xmlrpcString']);
				break;
				// <G_Giunta_2001-02-29>
				// Add support for encoding/decoding of booleans, since they are supported in PHP
			case 'boolean':
				$xmlrpc_val->addScalar($php_val, $GLOBALS['xmlrpcBoolean']);
				break;
				// </G_Giunta_2001-02-29>
			// catch "resource", "NULL", "user function", "unknown type"
			//case 'unknown type':
			default:
				// giancarlo pinerolo <ping@alt.it>
				// it has to return
				// an empty object in case (which is already
				// at this point), not a boolean.
				break;
			}
			return $xmlrpc_val;
	}

	/**
	* decode a string that is encoded w/ "chunked" transfer encoding
	* as defined in rfc2068 par. 19.4.6
	* code shamelessly stolen from nusoap library by Dietrich Ayala
	*
	* @param   string $buffer the string to be decoded
	* @return  string
	*/
	function decode_chunked($buffer)
	{
		// length := 0
		$length = 0;
		$new = '';

		// read chunk-size, chunk-extension (if any) and crlf
		// get the position of the linebreak
		$chunkend = strpos($buffer,"\r\n") + 2;
		$temp = substr($buffer,0,$chunkend);
		$chunk_size = hexdec( trim($temp) );
		$chunkstart = $chunkend;
		// while(chunk-size > 0) {
		while($chunk_size > 0)
		{
			$chunkend = strpos($buffer, "\r\n", $chunkstart + $chunk_size);

			// just in case we got a broken connection
			if($chunkend == false)
			{
				$chunk = substr($buffer,$chunkstart);
				// append chunk-data to entity-body
				$new .= $chunk;
				$length += strlen($chunk);
				break;
			}

			// read chunk-data and crlf
			$chunk = substr($buffer,$chunkstart,$chunkend-$chunkstart);
			// append chunk-data to entity-body
			$new .= $chunk;
			// length := length + chunk-size
			$length += strlen($chunk);
			// read chunk-size and crlf
			$chunkstart = $chunkend + 2;

			$chunkend = strpos($buffer,"\r\n",$chunkstart)+2;
			if($chunkend == false)
			{
				break; //just in case we got a broken connection
			}
			$temp = substr($buffer,$chunkstart,$chunkend-$chunkstart);
			$chunk_size = hexdec( trim($temp) );
			$chunkstart = $chunkend;
		}
		return $new;
	}

	/**
	* Given a string defining a php type or phpxmlrpc type (loosely defined: strings
	* accepted come from javadoc blocks), return corresponding phpxmlrpc type.
	* NB: for php 'resource' types returns empty string, since resources cannot be serialized;
	* for php class names returns 'struct', since php objects can be serialized as xmlrpc structs
	* @param string $phptype
	* @return string
	*/
	function php_2_xmlrpc_type($phptype)
	{
		switch(strtolower($phptype))
		{
			case 'string':
				return $GLOBALS['xmlrpcString'];
			case 'integer':
			case $GLOBALS['xmlrpcInt']: // 'int'
			case $GLOBALS['xmlrpcI4']:
				return $GLOBALS['xmlrpcInt'];
			case 'double':
				return $GLOBALS['xmlrpcDouble'];
			case 'boolean':
				return $GLOBALS['xmlrpcBoolean'];
			case 'array':
				return $GLOBALS['xmlrpcArray'];
			case 'object':
				return $GLOBALS['xmlrpcStruct'];
			case $GLOBALS['xmlrpcBase64']:
			case $GLOBALS['xmlrpcStruct']:
				return strtolower($phptype);
			case 'resource':
				return '';
			default:
				if(class_exists($phptype))
				{
					return $GLOBALS['xmlrpcStruct'];
				}
				else
				{
					// unknown: might be any xmlrpc type
					return $GLOBALS['xmlrpcValue'];
				}
		}
	}

	/**
	* Given a user-defined PHP function, create a PHP 'wrapper' function that can
	* be exposed as xmlrpc method from an xmlrpc_server object and called from remote
	* clients.
	*
	* Since php is a typeless language, to infer types of input and output parameters,
	* it relies on parsing the javadoc-style comment block associated with the given
	* function. Usage of xmlrpc native types (such as datetime.dateTime.iso8601 and base64)
	* in the @param tag is also allowed, if you need the php function to receive/send
	* data in that particular format (note that base64 enncoding/decoding is transparently
	* carried out by the lib, while datetime vals are passed around as strings)
	*
	* Known limitations:
	* - requires PHP 5.0.3 +
	* - only works for user-defined functions, not for PHP internal functions
	*   (reflection does not support retrieving number/type of params for those)
	* - functions returning php objects will generate special xmlrpc responses:
	*   when the xmlrpc decoding of those responses is carried out by this same lib, using
	*   the appropriate param in php_xmlrpc_decode, the php objects will be rebuilt.
	*   In short: php objects can be serialized, too (except for their resource members),
	*   using this function.
	*   Other libs might choke on the very same xml that will be generated in this case
	*   (i.e. it has a nonstandard attribute on struct element tags)
	* - usage of javadoc @param tags using param names in a different order from the
	*   function prototype is not considered valid (to be fixed?)
	*
	* Note that since rel. 2.0RC3 the preferred method to have the server call 'standard'
	* php functions (ie. functions not expecting a single xmlrpcmsg obj as parameter)
	* is by making use of the functions_parameters_type class member.
	*
	* @param string $funcname the name of the PHP user function to be exposed as xmlrpc method; array($obj, 'methodname') might be ok too, in the future...
	* @return false on error, or an array containing the name of the new php function,
	*         its signature and docs, to be used in the server dispatch map
	*
	* @todo decide how to deal with params passed by ref: bomb out or allow?
	* @todo finish using javadoc info to build method sig if all params are named but out of order
	* @done switch to some automagic object encoding scheme
	* @todo add a check for params of 'resource' type
	* @todo add some trigger_errors when returning false?
	* @todo what to do when the PHP function returns NULL? we are currently returning bogus responses!!!
	*/
	function wrap_php_function($funcname, $newfuncname='')
	{
		if(version_compare(phpversion(), '5.0.3') == -1)
		{
			// up to php 5.0.3 some useful reflection methods were missing
			return false;
		}
		if((is_array($funcname) && !method_exists($funcname[0], $funcname[1])) || !function_exists($funcname))
		{
			return false;
		}
		else
		{
			// determine name of new php function
			if($newfuncname == '')
			{
				if(is_array($funcname))
				{
					$xmlrpcfuncname = "xmlrpc_".implode('_', $funcname);
				}
				else
				{
					$xmlrpcfuncname = "xmlrpc_$funcname";
				}
			}
			else
			{
				$xmlrpcfuncname = $newfuncname;
			}
			while(function_exists($xmlrpcfuncname))
			{
				$xmlrpcfuncname .= 'x';
			}
			$code = "function $xmlrpcfuncname(\$msg) {\n";

			// start to introspect PHP code
			$func =& new ReflectionFunction($funcname);
			if($func->isInternal())
			{
				// Note: from PHP 5.1.0 onward, we will possibly be able to use invokeargs
				// instead of getparameters to fully reflect internal php functions ?
				return false;
			}

			// retrieve parameter names, types and description from javadoc comments

			// function description
			$desc = '';
			// type of return val: by default 'any'
			$returns = $GLOBALS['xmlrpcValue'];
			// type + name of function parameters
			$paramDocs = array();

			$docs = $func->getDocComment();
			if($docs != '')
			{
				$docs = explode("\n", $docs);
				$i = 0;
				foreach($docs as $doc)
				{
					$doc = trim($doc, " \r\t/*");
					if(strlen($doc) && strpos($doc, '@') !== 0 && !$i)
					{
						if($desc)
						{
							$desc .= "\n";
						}
						$desc .= $doc;
					}
					elseif(strpos($doc, '@param') === 0)
					{
						// syntax: @param type [$name] desc
						if(preg_match('/@param\s+(\S+)(\s+\$\S+)?\s+(.+)/', $doc, $matches))
						{
							if(strpos($matches[1], '|'))
							{
								//$paramDocs[$i]['type'] = explode('|', $matches[1]);
								$paramDocs[$i]['type'] = 'mixed';
							}
							else
							{
								$paramDocs[$i]['type'] = $matches[1];
							}
							$paramDocs[$i]['name'] = trim($matches[2]);
							$paramDocs[$i]['doc'] = $matches[3];
						}
						$i++;
					}
					elseif(strpos($doc, '@return') === 0)
					{
						$returns = preg_split("/\s+/", $doc);
						if(isset($returns[1]))
						{
							$returns = php_2_xmlrpc_type($returns[1]);
						}
					}
				}
			}

			// start introspection of actual function prototype and building of PHP code
			// to be eval'd
			$params = $func->getParameters();

			$innercode = '';
			$i = 0;
			$parsvariations = array();
			$pars = array();
			$pnum = count($params);
			foreach($params as $param)
			{
				if (isset($paramDocs[$i]['name']) && $paramDocs[$i]['name'] && strtolower($paramDocs[$i]['name']) != '$'.strtolower($param->getName()))
				{
					// param name from phpdoc info does not match param definition!
					$paramDocs[$i]['type'] = 'mixed';
				}

				if($param->isOptional())
				{
					// this particular parameter is optional. save as valid previous list of parameters
					$innercode .= "if (\$paramcount > $i) {\n";
					$parsvariations[] = $pars;
				}
				$innercode .= "\$p$i = \$msg->getParam($i);\n";
				$innercode .= "if (\$p{$i}->kindOf() == 'scalar') \$p$i = \$p{$i}->scalarval(); else \$p$i = php_xmlrpc_decode(\$p$i);\n";
				$pars[] = "\$p$i";
				$i++;
				if($param->isOptional())
				{
					$innercode .= "}\n";
				}
				if($i == $pnum)
				{
					// last allowed parameters combination
					$parsvariations[] = $pars;
				}
			}

			$sigs = array();
			if(count($parsvariations) == 0)
			{
				// only known good synopsis = no parameters
				$parsvariations[] = array();
				$minpars = 0;
			}
			else
			{
				$minpars = count($parsvariations[0]);
			}

			if($minpars)
			{
				// add to code the check for min params number
				// NB: this check needs to be done BEFORE decoding param values
				$innercode = "\$paramcount = \$msg->getNumParams();\n" .
				"if (\$paramcount < $minpars) return new xmlrpcresp(0, {$GLOBALS['xmlrpcerr']['incorrect_params']}, '{$GLOBALS['xmlrpcstr']['incorrect_params']}');\n" . $innercode;
			}
			else
			{
				$innercode = "\$paramcount = \$msg->getNumParams();\n" . $innercode;
			}

			$innercode .= "\$np = false;";
			foreach($parsvariations as $pars)
			{
				$innercode .= "if (\$paramcount == " . count($pars) . ") \$retval = $funcname(" . implode(',', $pars) . "); else\n";
				// build a 'generic' signature (only use an appropriate return type)
				$sig = array($returns);
				for($i=0; $i < count($pars); $i++)
				{
					if (isset($paramDocs[$i]['type']))
					{
						$sig[] = php_2_xmlrpc_type($paramDocs[$i]['type']);
					}
					else
					{
						$sig[] = $GLOBALS['xmlrpcValue'];
					}
				}
				$sigs[] = $sig;
			}
			$innercode .= "\$np = true;\n";
			$innercode .= "if (\$np) return new xmlrpcresp(0, {$GLOBALS['xmlrpcerr']['incorrect_params']}, '{$GLOBALS['xmlrpcstr']['incorrect_params']}'); else\n";
			//$innercode .= "if (\$_xmlrpcs_error_occurred) return new xmlrpcresp(0, $GLOBALS['xmlrpcerr']user, \$_xmlrpcs_error_occurred); else\n";
			if($returns == $GLOBALS['xmlrpcDateTime'] || $returns == $GLOBALS['xmlrpcBase64'])
			{
				$innercode .= "return new xmlrpcresp(new xmlrpcval(\$retval, '$returns'));";
			}
			else
			{
				$innercode .= "return new xmlrpcresp(php_xmlrpc_encode(\$retval, array('encode_php_objs')));";
			}
			// shall we exclude functions returning by ref?
			// if($func->returnsReference())
			//  return false;
			$code = $code . $innercode . "\n}\n \$allOK=1;";
			//print_r($code);
			$allOK = 0;
			eval($code);
			// alternative
			//$xmlrpcfuncname = create_function('$m', $innercode);

			if(!$allOK)
			{
				return false;
			}

			/// @todo examine if $paramDocs matches $parsvariations and build array for
			/// usage as method signature, plus put together a nice string for docs

			$ret = array('function' => $xmlrpcfuncname, 'signature' => $sigs, 'docstring' => $desc);
			return $ret;
		}
	}

	/**
	* Given an xmlrpc client and a method name, register a php wrapper function
	* that will call it and return results using native php types for both
	* params and results. The generated php function will return an xmlrpcresp
	* oject for failed xmlrpc calls
	*
	* Known limitations:
	* - server must support system.methodsignature for the wanted xmlrpc method
	* - for methods that expose many signatures, only one can be picked (we
	*   could in priciple check if signatures differ only by number of params
	*   and not by type, but it would be more complication than we can spare time)
	* - nested xmlrpc params: the caller of the generated php function has to
	*   encode on its own the params passed to the php function if these are structs
	*   or arrays whose (sub)members include values of type datetime or base64
	*
	* Notes: the connection properties of the given client will be copied
	* and reused for the connection used during the call to the generated
	* php function.
	* Calling the generated php function 'might' be slow: a new xmlrpc client
	* is created on every invocation and an xmlrpc-connection opened+closed.
	* An extra 'debug' param is appended to param list of xmlrpc method, useful
	* for debugging purposes.
	*
	* @param xmlrpc_client $client     an xmlrpc client set up correctly to communicate with target server
	* @param string        $methodname the xmlrpc method to be mapped to a php function
	* @param integer       $signum     the index of the method signature to use in mapping (if method exposes many sigs)
	* @return string                   the name of the generated php function (or false)
	*/
	function wrap_xmlrpc_method($client, $methodname, $signum=0, $timeout=0, $protocol='', $newfuncname='')
	{
		$msg =& new xmlrpcmsg('system.methodSignature');
		$msg->addparam(new xmlrpcval($methodname));
		$response =& $client->send($msg, $timeout, $protocol);
		if(!$response || $response->faultCode())
		{
			return false;
		}
		else
		{
			$desc = $response->value();
			if($desc->kindOf() != 'array' || $desc->arraysize() <= $signum)
			{
				return false;
			}
			else
			{
				if($newfuncname != '')
				{
					$xmlrpcfuncname = $newfuncname;
				}
				else
				{
					$xmlrpcfuncname = 'xmlrpc_'.str_replace('.', '_', $methodname);
				}
				while(function_exists($xmlrpcfuncname))
				{
					$xmlrpcfuncname .= 'x';
				}
				$desc = $desc->arraymem($signum);
				$code = "function $xmlrpcfuncname (";
				$innercode = "\$client =& new xmlrpc_client('$client->path', '$client->server');\n";
				// copy all client fields to the client that will be generated runtime
				// (this provides for future expansion of client obj)
				foreach($client as $fld => $val)
				{
					if($fld != 'debug' && $fld != 'return_type')
					{
						$val = var_export($val, true);
						$innercode .= "\$client->$fld = $val;\n";
					}
				}
				$innercode .= "\$client->setDebug(\$debug);\n";
				$innercode .= "\$client->return_type = 'xmlrpcvals';\n";
				$innercode .= "\$msg =& new xmlrpcmsg('$methodname');\n";

				// param parsing
				$plist = array();
				$pcount = $desc->arraysize();
				for($i = 1; $i < $pcount; $i++)
				{
					$plist[] = "\$p$i";
					$ptype = $desc->arraymem($i);
					$ptype = $ptype->scalarval();
					if($ptype == 'dateTime.iso8601' || $ptype == 'base64')
					{
						$innercode .= "\$p$i =& new xmlrpcval(\$p$i, '$ptype');\n";
					}
					else
					{
						$innercode .= "\$p$i =& php_xmlrpc_encode(\$p$i);\n";
					}
					$innercode .= "\$msg->addparam(\$p$i);\n";
				}
				$plist[] = '$debug = 0';
				$plist = implode(',', $plist);

				$innercode .= "\$res =& \$client->send(\$msg, $timeout, '$protocol');\n";
				$innercode .= "if (\$res->faultcode()) return \$res; else return php_xmlrpc_decode(\$res->value(), array('decode_php_objs'));";

				$code = $code . $plist. ") {\n" . $innercode . "\n}\n\$allOK=1;";
				//print_r($code);
				$allOK = 0;
				eval($code);
				// alternative
				//$xmlrpcfuncname = create_function('$m', $innercode);
				if($allOK)
				{
					return $xmlrpcfuncname;
				}
				else
				{
					return false;
				}
			}
		}
	}

	/**
	* xml charset encoding guessing helper function.
	* Tries to determine the charset encoding of an XML chunk
	* received over HTTP.

	* NB: according to the spec (RFC 3023, if text/xml content-type is received over HTTP without a content-type,

	* we SHOULD assume it is strictly US-ASCII. But we try to be more tolerant of unconforming (legacy?) clients/servers,

	* which will be most probably using UTF-8 anyway...
	*
	* @param string $httpheaders the http Content-type header
	* @param string $xmlchunk xml content buffer
	* @param string $encoding_prefs comma separated list of character encodings to be used as default (when mb extension is enabled)
	*
	* @todo explore usage of mb_http_input(): does it detect http headers + post data? if so, use it instead of hand-detection!!!
	*/
	function guess_encoding($httpheader='', $xmlchunk='', $encoding_prefs=null)
	{
		// discussion: see http://www.yale.edu/pclt/encoding/
		// 1 - test if encoding is specified in HTTP HEADERS

		//Details:
		// LWS:           (\13\10)?( |\t)+
		// token:         (any char but excluded stuff)+
		// header:        Content-type = ...; charset=value(; ...)*
		//   where value is of type token, no LWS allowed between 'charset' and value
		// Note: we do not check for invalid chars in VALUE:
		//   this had better be done using pure ereg as below

		/// @todo this test will pass if ANY header has charset specification, not only Content-Type. Fix it?
		if(eregi(";((\\xD\\xA)?[ \\x9]+)*charset=", $httpheader))
		{
			/// @BUG if charset is received uppercase, this line will fail!
			$in = strpos($httpheader, 'charset=')+8;
			$out = strpos($httpheader, ';', $in) ? strpos($httpheader, ';', $in) : strlen($httpheader);
			return strtoupper(trim(substr($httpheader, $in, $out-$in)));
		}

		// 2 - scan the first bytes of the data for a UTF-16 (or other) BOM pattern
		//     (source: http://www.w3.org/TR/2000/REC-xml-20001006)
		//     NOTE: actually, according to the spec, even if we find the BOM and determine
		//     an encoding, we should check if there is an encoding specified
		//     in the xml declaration, and verify if they match.
		/// @todo implement check as described above?
		/// @todo implement check for first bytes of string even without a BOM? (It sure looks harder than for cases WITH a BOM)
		if(@ereg("^(\\x00\\x00\\xFE\\xFF|\\xFF\\xFE\\x00\\x00|\\x00\\x00\\xFF\\xFE|\\xFE\\xFF\\x00\\x00)", $xmlchunk))
		//  if (preg_match("/^(\\x00\\x00\\xFE\\xFF|\\xFF\\xFE\\x00\\x00|\\x00\\x00\\xFF\\xFE|\\xFE\\xFF\\x00\\x00)/", $xmlchunk))
		{
			return 'UCS-4';
		}
		elseif(ereg("^(\\xFE\\xFF|\\xFF\\xFE)", $xmlchunk))
		{
			return 'UTF-16';
		}
		elseif(ereg("^(\\xEF\\xBB\\xBF)", $xmlchunk))
		{
			return 'UTF-8';
		}

		// 3 - test if encoding is specified in the xml declaration
		// Details:
		// SPACE:         (#x20 | #x9 | #xD | #xA)+ === [ \x9\xD\xA]+
		// EQ:            SPACE?=SPACE? === [ \x9\xD\xA]*=[ \x9\xD\xA]*
		if (ereg("^<\?xml".
			"[ \\x9\\xD\\xA]+" . "version"  . "[ \\x9\\xD\\xA]*=[ \\x9\\xD\\xA]*" . "((\"[a-zA-Z0-9_.:-]+\")|('[a-zA-Z0-9_.:-]+'))".
			"[ \\x9\\xD\\xA]+" . "encoding" . "[ \\x9\\xD\\xA]*=[ \\x9\\xD\\xA]*" . "((\"[A-Za-z][A-Za-z0-9._-]*\")|('[A-Za-z][A-Za-z0-9._-]*'))",
			$xmlchunk, $regs))
		{
			return strtoupper(substr($regs[4], 1, strlen($regs[4])-2));
		}

		// 4 - if mbstring is available, let it do the guesswork
		// NB: we favour finding an encoding that is compatible with what we can process
		if(extension_loaded('mbstring'))
		{
			if($encoding_prefs)
			{
				$enc = mb_detect_encoding($xmlchunk, $encoding_prefs);
			}
			else
			{
				$enc = mb_detect_encoding($xmlchunk);
			}
			// NB: mb_detect likes to call it ascii, xml parser likes to call it US_ASCII...
			// IANA also likes better US-ASCII, so go with it
			if($enc == 'ASCII')
			{
				$enc = 'US-'.$enc;
			}
			return $enc;
		}
		else
		{
			// no encoding specified: as per HTTP1.1 assume it is iso-8859-1?
			// Both RFC 2616 (HTTP 1.1) and 1945(http 1.0) clearly state that for text/xxx content types
			// this should be the standard. And we should be getting text/xml as request and response.
			// BUT we have to be backward compatible with the lib, which always used UTF-8 as default...
			return $GLOBALS['xmlrpc_defencoding'];
		}
	}

/**
* Checks if a given charset encoding is present in a list of encodings or
* if it is a valid subset of any encoding in the list
* @param string $encoding  charset to be tested
* @param mixed  $validlist comma separated list of valid charsets (or array of charsets)
*/
function is_valid_charset($encoding, $validlist)
{
	$charset_supersets = array(
    'US-ASCII' => array ('ISO-8859-1', 'ISO-8859-2', 'ISO-8859-3', 'ISO-8859-4',
                         'ISO-8859-5', 'ISO-8859-6', 'ISO-8859-7', 'ISO-8859-8',
                         'ISO-8859-9', 'ISO-8859-10', 'ISO-8859-11', 'ISO-8859-12',
                         'ISO-8859-13', 'ISO-8859-14', 'ISO-8859-15', 'UTF-8',
                         'EUC-JP', 'EUC-', 'EUC-KR', 'EUC-CN')
	);
	if (is_string($validlist))
		$validlist = split(',', $validlist);
	if (@in_array(strtoupper($encoding), $validlist))
		return true;
	else
	{
		if (array_key_exists($encoding, $charset_supersets))
			foreach ($validlist as $allowed)
				if (in_array($allowed, $charset_supersets[$encoding]))
					return true;
		return false;
	}
}

?>