# 'Request' example added jjk  11/20/98

import win32ui  # isort: skip # Must be imported before dde !
import dde

server = dde.CreateServer()
server.Create("TestClient")

conversation = dde.CreateConversation(server)

conversation.ConnectTo("RunAny", "RunAnyCommand")
conversation.Exec("DoSomething")
conversation.Exec("DoSomethingElse")

conversation.ConnectTo("RunAny", "ComputeStringLength")
s = "abcdefghi"
sl = conversation.Request(s)
print(f'length of "{s}" is {sl}')
