
var MBstrBundleService = Components.classes["@mozilla.org/intl/stringbundle;1"].
			getService(Components.interfaces.nsIStringBundleService);
var mboximportbundle = MBstrBundleService.createBundle("chrome://openerp_plugin/locale/mboximport.properties"); 


function saveMsgAsEML(msguri,file,append,uriArray,hdrArray,fileArray) {
	
    var myEMLlistner = {
	   
		scriptStream : null,
		emailtext : "",

        QueryInterface : function(iid)  {
                if (iid.equals(Components.interfaces.nsIStreamListener) ||   
                    iid.equals(Components.interfaces.nsIMsgHeaderSink) ||
                    iid.equals(Components.interfaces.nsISupports))
                 return this;
        
                throw Components.results.NS_NOINTERFACE;
                return 0;
        },
        
        onStartRequest : function (aRequest, aContext) { 
			this.scriptStream = Components.classes['@mozilla.org/binaryinputstream;1'].createInstance(Components.interfaces.nsIBinaryInputStream);
        },
            
        onStopRequest : function (aRequest, aContext, aStatusCode) {
			this.scriptStream = null;
						
			if (append) {
				if (this.emailtext != "") {
					var data = this.emailtext + "\n";
					// Some Imap servers don't add to the message the "From" prologue
					if (data && ! data.match(/^From/)) {
						var now = new Date;
						var prologue = "From - " + now.toString() + "\n";
						data = prologue+data;
					}
					data = IETescapeBeginningFrom(data);
				}
				var fileClone = file.clone();
				IETwriteDataOnDisk(fileClone,data,true,this.sub,null);
			}
			else {
				if (! hdrArray)
					var sub = getSubjectForHdr(hdr);
				else {
					var parts = hdrArray[IETexported].split("§][§^^§");
					var sub = parts[4];
				}
			
				var data = this.emailtext.replace(/^From.+\r?\n]/, "");
				data = IETescapeBeginningFrom(data);
				var clone = file.clone();
				// The name is taken from the subject "corrected"
				clone.append(sub+".eml");
				clone.createUnique(0,0644);
				var time = (hdr.dateInSeconds)*1000;
				IETwriteDataOnDisk(clone,data,false,null,time);
			}
			IETexported = IETexported + 1;
			IETwritestatus(mboximportbundle.GetStringFromName("exported")+" "+IETexported+" "+mboximportbundle.GetStringFromName("msgs")+" "+IETtotal);
			
			if (IETexported < IETtotal) {
				if (fileArray) {
					var nextUri = uriArray[IETexported];
					var nextFile = fileArray[IETexported];
				}
				else if (! hdrArray) {
					var nextUri = uriArray[IETexported];
					var nextFile = file;
				}
				else {
					parts = hdrArray[IETexported].split("§][§^^§");
					var nextUri = parts[5];
					var nextFile = file;
				}
				saveMsgAsEML(nextUri,nextFile,append,uriArray,hdrArray,fileArray);
			}
			else {
				IETexported = 0;
				IETtotal = 0;
			}
		},
            
        onDataAvailable : function (aRequest, aContext, aInputStream, aOffset, aCount) {
			this.scriptStream.setInputStream(aInputStream);
			var chunk = this.scriptStream.readBytes(aCount);
           	this.emailtext += chunk;
	     }        
        };
	var mms = messenger.messageServiceFromURI(msguri).QueryInterface(Components.interfaces.nsIMsgMessageService);
	var hdr = mms.messageURIToMsgHdr(msguri);
	mms.streamMessage(msguri, myEMLlistner, msgWindow, null, false, null);
}


function nametoascii(str) {
	if (! gPrefBranch.getBoolPref("mboximport.export.filenames_toascii")) {
		str = str.replace(/[\x00-\x19]/g,"_");
		return str.replace(/[\/\\:,<>*\?\"\|]/g,"_");
	}
	if (str)
		str = str.replace(/[^a-zA-Z0-9]/g,"_");
	else
		str = "Undefinied_or_empty";
	return str;
}


function  IETwriteDataOnDisk(file,data,append,name,time) {
	var foStream = Components.classes["@mozilla.org/network/file-output-stream;1"]
		.createInstance(Components.interfaces.nsIFileOutputStream);
	if (append) {
		file.append(name);
		foStream.init(file, 0x02 | 0x08 | 0x10, 0664, 0); // write,  create, append
	}
	else 
		foStream.init(file, 0x02 | 0x08 | 0x20, 0664, 0); // write, create, truncate
	if (data)
		foStream.write(data,data.length);
	foStream.close();
	var prefs = Components.classes["@mozilla.org/preferences-service;1"]
		.getService(Components.interfaces.nsIPrefBranch);
	if (time && prefs.getBoolPref("mboximport.export.set_filetime"))
		file.lastModifiedTime = time;
}



function IETescapeBeginningFrom(data) {
	// Workaround to fix the "From " in beginning line problem in body messages
	// See https://bugzilla.mozilla.org/show_bug.cgi?id=119441 and
	// https://bugzilla.mozilla.org/show_bug.cgi?id=194382
	// TB2 has uncorrect beahviour with html messages
	// This is not very fine, but I didnt' find anything better...
	var datacorrected = data.replace(/\nFrom /g, "\n From ");
	return datacorrected;
}


function getPredefinedFolder(type) {
	var prefs = Components.classes["@mozilla.org/preferences-service;1"]
		.getService(Components.interfaces.nsIPrefBranch);
	// type 0 = folder
	// type 1 = all messages
	// type 2 = selected messages

	var use_dir = "mboximport.exportMSG.use_dir";
    var dirService = Components.classes["@mozilla.org/file/directory_service;1"].
    	getService(Components.interfaces.nsIProperties).get("Home", Components.interfaces.nsIFile);
    var homeDir = dirService.path;
    var dir_path = ((homeDir.search(/\\/) != -1) ? homeDir + "\\" : homeDir + "/")
	try {
		var localFile = Components.classes["@mozilla.org/file/local;1"].createInstance(Components.interfaces.nsILocalFile);
		localFile.initWithPath(dir_path);
		return localFile;

	}
	catch(e) {
		return null;
	}
}

﻿function getSubjectForHdr(hdr) {
	var emlNameType = gPrefBranch.getIntPref("mboximport.exportEML.filename_format");	
	var mustcorrectname = gPrefBranch.getBoolPref("mboximport.export.filenames_toascii");
	var subMaxLen = gPrefBranch.getIntPref("mboximport.subject.max_length")-1;
	if (hdr.mime2DecodedSubject)

		var subj = hdr.mime2DecodedSubject.substring(0, subMaxLen);
	else
		var subj =IETnosub;
	subj = nametoascii(subj);
	var dateInSec = hdr.dateInSeconds;
	var msgDate8601string = dateInSecondsTo8601(dateInSec);
	var key = hdr.messageKey;
	if (emlNameType == 2) {
		var pattern = gPrefBranch.getCharPref("mboximport.export.filename_pattern");
		pattern = pattern.replace("%s",subj);
    	pattern = pattern.replace("%k",key);
		pattern = pattern.replace("%d", msgDate8601string);
		pattern = pattern.replace(/-%e/g, "");
		pattern = pattern.replace(/[\x00-\x19]/g,"_");
		var fname = pattern;
	}
	else {

		var fname = msgDate8601string+"-"+subj+"-"+hdr.messageKey;
	}
	setFileName(fname)
	fname = fname.replace(/[\x00-\x19]/g,"_");
	if (mustcorrectname)
		fname = nametoascii(fname);
	else
		fname = fname.replace(/[\/\\:,<>*\?\"\|]/g,"_");
	return fname;
}

function dateInSecondsTo8601(secs) {
	var addTime = gPrefBranch.getBoolPref("mboximport.export.filenames_addtime");
	var msgDate = new Date(secs*1000);
	var msgDate8601 = msgDate.getFullYear();
	if (msgDate.getMonth() < 9)
		var month = "0"+(msgDate.getMonth()+1);
	else
		var month = msgDate.getMonth()+1;
	if (msgDate.getDate() < 10)
		var day = "0"+ msgDate.getDate();
	else
		var day = msgDate.getDate();
	var msgDate8601string = msgDate8601.toString()+month.toString()+day.toString();
	if (addTime &&  gPrefBranch.getIntPref("mboximport.exportEML.filename_format") == 2) {
		if (msgDate.getHours() < 10)
			var hours = "0"+msgDate.getHours();
		else
			var hours = msgDate.getHours();
		if (msgDate.getMinutes() < 10)
			var min = "0"+msgDate.getMinutes();
		else
			var min = msgDate.getMinutes();
		msgDate8601string += "-"+ hours.toString() + min.toString();
	}
	return msgDate8601string;
}

function IETwritestatus(text) {
	document.getElementById("statusText").setAttribute("label", text);
	var prefs = Components.classes["@mozilla.org/preferences-service;1"].getService(Components.interfaces.nsIPrefBranch);
	var delay = prefs.getIntPref("mboximport.delay.clean_statusbar");
	if (delay > 0)
		window.setTimeout(function(){IETdeletestatus(text);}, delay);
}

function IETdeletestatus(text) {
	if (document.getElementById("statusText").getAttribute("label") == text)
		document.getElementById("statusText").setAttribute("label", "");
}


