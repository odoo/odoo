var db = '';
var ip = '';
var USER = '';
var PWD = '';
SESSION = new oe.base.Session('DEBUG');
SESSION.login(db,USER,PWD, initLogin);

function initLogin() {
	// Le premier argument de la fonction -> référence à une fonction python.
	SESSION.rpc("/web_mobile/mobile/load_user", {},  function getResult (result){

	// ici le corps de ta fonction si la requete rpc est réussite

	},  function getErrormyerror(e) {
	// ici le corps de ta fonction d'échec.
		alert('error during users loading');
		alert(e.data.debug);
	});
}


