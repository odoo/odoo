# module and export all
snippet mod
	-module(${1:`Filename('', 'my')`}).
	
	-compile([export_all]).
	
	start() ->
	    ${2}
	
	stop() ->
	    ok.
# define directive
snippet def
	-define(${1:macro}, ${2:body}).${3}
# export directive
snippet exp
	-export([${1:function}/${2:arity}]).
# include directive
snippet inc
	-include("${1:file}").${2}
# behavior directive
snippet beh
	-behaviour(${1:behaviour}).${2}
# if expression
snippet if
	if
	    ${1:guard} ->
	        ${2:body}
	end
# case expression
snippet case
	case ${1:expression} of
	    ${2:pattern} ->
	        ${3:body};
	end
# anonymous function
snippet fun
	fun (${1:Parameters}) -> ${2:body} end${3}
# try...catch
snippet try
	try
	    ${1}
	catch
	    ${2:_:_} -> ${3:got_some_exception}
	end
# record directive
snippet rec
	-record(${1:record}, {
	    ${2:field}=${3:value}}).${4}
# todo comment
snippet todo
	%% TODO: ${1}
## Snippets below (starting with '%') are in EDoc format.
## See http://www.erlang.org/doc/apps/edoc/chapter.html#id56887 for more details
# doc comment
snippet %d
	%% @doc ${1}
# end of doc comment
snippet %e
	%% @end
# specification comment
snippet %s
	%% @spec ${1}
# private function marker
snippet %p
	%% @private
# OTP application
snippet application
	-module(${1:`Filename('', 'my')`}).

	-behaviour(application).

	-export([start/2, stop/1]).

	start(_Type, _StartArgs) ->
	    case ${2:root_supervisor}:start_link() of
	        {ok, Pid} ->
	            {ok, Pid};
	        Other ->
		          {error, Other}
	    end.

	stop(_State) ->
	    ok.	
# OTP supervisor
snippet supervisor
	-module(${1:`Filename('', 'my')`}).

	-behaviour(supervisor).

	%% API
	-export([start_link/0]).

	%% Supervisor callbacks
	-export([init/1]).

	-define(SERVER, ?MODULE).

	start_link() ->
	    supervisor:start_link({local, ?SERVER}, ?MODULE, []).

	init([]) ->
	    Server = {${2:my_server}, {$2, start_link, []},
	      permanent, 2000, worker, [$2]},
	    Children = [Server],
	    RestartStrategy = {one_for_one, 0, 1},
	    {ok, {RestartStrategy, Children}}.
# OTP gen_server
snippet gen_server
	-module(${1:`Filename('', 'my')`}).

	-behaviour(gen_server).

	%% API
	-export([
	         start_link/0
	        ]).

	%% gen_server callbacks
	-export([init/1, handle_call/3, handle_cast/2, handle_info/2,
	         terminate/2, code_change/3]).

	-define(SERVER, ?MODULE).

	-record(state, {}).

	%%%===================================================================
	%%% API
	%%%===================================================================

	start_link() ->
	    gen_server:start_link({local, ?SERVER}, ?MODULE, [], []).

	%%%===================================================================
	%%% gen_server callbacks
	%%%===================================================================

	init([]) ->
	    {ok, #state{}}.

	handle_call(_Request, _From, State) ->
	    Reply = ok,
	    {reply, Reply, State}.

	handle_cast(_Msg, State) ->
	    {noreply, State}.

	handle_info(_Info, State) ->
	    {noreply, State}.

	terminate(_Reason, _State) ->
	    ok.

	code_change(_OldVsn, State, _Extra) ->
	    {ok, State}.

	%%%===================================================================
	%%% Internal functions
	%%%===================================================================

