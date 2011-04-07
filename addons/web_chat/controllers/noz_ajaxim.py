
import im
from server import main # import the server library

im = Webchat_IM()
action = preg_replace('/^' . preg_quote($_SERVER['SCRIPT_NAME'], '/') . '\/(.+?)(\?.+)?$/', '\1', $_SERVER['REQUEST_URI']);

if(substr(action, 0, 1) != '_' && method_exists(im, action))
    if(action == 'poll') {
        if($_GET['method'] == 'comet') {
            im->poll('comet');
        } else {
            print $_GET['callback'] . '(' . json_encode(im->poll($_GET['method'])) . ')';
        }
    } else {
        execute = call_user_func_array(array(im, action), $_POST);
        if(execute)
            print json_encode(execute !== false ? execute : array('e'=>'wrong args'));
    }
else
    print json_encode(array('e'=>'no method'));