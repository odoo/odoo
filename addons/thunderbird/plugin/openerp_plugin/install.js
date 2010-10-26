// constants
const APP_DISPLAY_NAME = "OpenERP Thunderbird Plugins";
const APP_NAME = "OpenERP";
const APP_VERSION = "1.0";
const WARNING = "WARNING: You need administrator privileges to install OpenERP Thunderbird Plugin. It will be installed in the application directory for all users.";
const VERSION_ERROR = "This extension can only be installed in a version higher than 2.0";
const NOT_WRITABLE_ERROR = "This extension requires write access to the application directory to install properly."
const locales = [
	"en-US",
	null
];

// Gecko 1.7 doesn't support custom button labels
var incompatible = (typeof Install.BUTTON_POS_0 == "undefined");
if (incompatible)
	alert(VERSION_ERROR);

if (!incompatible) {
	// Check whether all directories can be accessed
	var dirList = [
		getFolder("Components"),
		getFolder(getFolder("Program", "defaults"), "pref")
	];
	for (var i = 0; i < dirList.length; i++)
		if (!File.isWritable(dirList[i]))
			incompatible = true;

	if (incompatible)
		alert(NOT_WRITABLE_ERROR);
}

if (!incompatible && confirm(WARNING, APP_DISPLAY_NAME)) {
	/* Pre-Install Cleanup (for prior versions) */

	// List of files to be checked
	var checkFiles = [
		[getFolder("Components"), "nsXmlRpcClient.js"],            // Root component
		[getFolder("Components"), "xml-rpc.xpt"],           // Component interface
			];

	// Remove any existing files
	initInstall("pre-install", "/rename", "0.0");  // open dummy-install
	for (var i = 0 ; i < checkFiles.length ; i++) {
		var currentDir = checkFiles[i][0];
		var name = checkFiles[i][1];
		var oldFile = getFolder(currentDir, name);

		// Find a name to rename the file into
		var newName = name + "-uninstalled";
		for (var n = 1; File.exists(oldFile) && File.exists(getFolder(currentDir, newName)); n++)
			newName = name + n + "-uninstalled";

		if (File.exists(oldFile))
			File.rename(oldFile, newName);
	}
	performInstall(); // commit renamed files

	/* Main part of the installation */

	var chromeType = DELAYED_CHROME;

	var files = [
		["components/nsXmlRpcClient.js", getFolder("Components")],
		["components/xml-rpc.xpt", getFolder("Components")],
		["defaults/preferences/tiny.js", getFolder(getFolder("Program", "defaults"), "pref")],
	];

	// initialize our install
	initInstall(APP_NAME, APP_PACKAGE, APP_VERSION);

	// Add files
	for (var i = 0; i < files.length; i++)
		addFile(APP_NAME, APP_VERSION, files[i][0], files[i][1], null);

	try {
		var err = registerChrome(CONTENT | chromeType, jar, "content/");
		if (err != SUCCESS)
			throw "Chrome registration for content failed (error code " + err + ").";

		err = registerChrome(SKIN | chromeType, jar, "skin/classic/");
		if (err != SUCCESS)
			throw "Chrome registration for skin failed (error code " + err + ").";

		for (i = 0; i < locales.length; i++) {
			if (!locales[i])
				continue;

			err = registerChrome(LOCALE | chromeType, jar, "locale/" + locales[i] + "/");
			if (err != SUCCESS)
				throw "Chrome registration for " + locales[i] + " locale failed (error code " + err + ").";
		}

		var err = performInstall();
		if (err != SUCCESS && err != 999)
			throw "Committing installation failed (error code " + err + ").";

		alert("OpenERP Thunderbird Plugin " + APP_VERSION + " is now installed.\n" +
					"It will become active after you restart your browser.");
	}
	catch (ex) {
		alert("Installation failed: " + ex + "\n" +
					"You probably don't have the necessary permissions (log in as system administrator).");
		cancelInstall(err);
	}
}
