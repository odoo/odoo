#!/usr/bin/env bash
set -eu -o pipefail

scheme=$1
domain=$2
database=$3
username=$4
password=$5

echo '<a id=common>'
curl "$scheme://$domain/RPC2" \
     --silent \
     -X POST \
     -H 'Content-Type: application/json' \
     -d @- <<EOF |
          {
               "jsonrpc": "2.0",
               "method": "version",
               "id": 0
          }
EOF
     jq -c 'if has("error") then halt_error else .result end'
echo '</a>'

echo '<a id=models>'
curl "$scheme://$domain/RPC2?db=$database" \
     --silent \
     -X POST \
     -H 'Content-Type: application/json' \
     --basic -u "$username:$password" \
     -d @- <<EOF |
          {
               "jsonrpc": "2.0",
               "method": "system.noop",
               "id": 0
          }
EOF
     jq -c 'if has("error") then halt_error else .result end'
echo '</a>'

echo '<a id=check_access_rights>'
curl "$scheme://$domain/RPC2?db=$database" \
     --silent \
     -X POST \
     -H 'Content-Type: application/json' \
     --basic -u "$username:$password" \
     -d @- <<EOF |
          {
               "jsonrpc": "2.0",
               "method": "res.partner.check_access_rights",
               "params": [{
                    "args": ["read"],
                    "kwargs": {
                         "raise_exception": false
                    }
               }],
               "id": 0
          }
EOF
     jq 'if has("error") then halt_error else .result end'
echo '</a>'

echo '<a id=list>'
record_ids=$(
     (
          curl "$scheme://$domain/RPC2?db=$database" \
               --silent \
               -X POST \
               -H 'Content-Type: application/json' \
               --basic -u "$username:$password" \
               -d @- | \
          jq -c 'if has("error") then halt_error else .result end'
     ) <<EOF
               {
                    "jsonrpc": "2.0",
                    "method": "res.partner.search",
                    "params": [{
                         "kwargs": {
                              "domain": [["is_company", "=", false]]
                         }
                    }],
                    "id": 0
               }
EOF
)
echo $record_ids
echo '</a>'

echo '<a id=pagination>'
curl "$scheme://$domain/RPC2?db=$database" \
     --silent \
     -X POST \
     -H 'Content-Type: application/json' \
     --basic -u "$username:$password" \
     -d @- <<EOF |
          {
               "jsonrpc": "2.0",
               "method": "res.partner.search",
               "params": [{
                    "kwargs": {
                         "domain": [["is_company", "=", false]],
                         "offset": 10,
                         "limit": 5
                    }
               }],
               "id": 0
          }
EOF
     jq -c 'if has("error") then halt_error else .result end'
echo '</a>'

echo '<a id=count>'
curl "$scheme://$domain/RPC2?db=$database" \
     --silent \
     -X POST \
     -H 'Content-Type: application/json' \
     --basic -u "$username:$password" \
     -d @- <<EOF |
          {
               "jsonrpc": "2.0",
               "method": "res.partner.search_count",
               "params": [{
                    "kwargs": {
                         "domain": [["is_company", "=", false]]
                    }
               }],
               "id": 0
          }
EOF
     jq 'if has("error") then halt_error else .result end'
echo '</a>'

echo '<a id=search_read>'
curl "$scheme://$domain/RPC2?db=$database" \
     --silent \
     -X POST \
     -H 'Content-Type: application/json' \
     --basic -u "$username:$password" \
     -d @- <<EOF |
          {
               "jsonrpc": "2.0",
               "method": "res.partner.search_read",
               "params": [{
                    "kwargs": {
                         "domain": [["is_company", "=", false]],
                         "fields": ["name", "title", "parent_name"],
                         "limit": 1
                    }
               }],
               "id": 0
          }
EOF
     jq 'if has("error") then halt_error else .result end'
echo '</a>'

echo '<a id=read>'
curl "$scheme://$domain/RPC2?db=$database" \
     --silent \
     -X POST \
     -H 'Content-Type: application/json' \
     --basic -u "$username:$password" \
     -d @- <<EOF |
          {
               "jsonrpc": "2.0",
               "method": "res.partner.read",
               "params": [{
                    "records": $record_ids,
                    "kwargs": {
                         "fields": ["name", "title", "parent_name"]
                    }
               }],
               "id": 0
          }
EOF
     jq 'if has("error") then halt_error else .result end'
echo '</a>'

echo '<a id=fields_get>'
curl "$scheme://$domain/RPC2?db=$database" \
     --silent \
     -X POST \
     -H 'Content-Type: application/json' \
     --basic -u "$username:$password" \
     -d @- <<EOF |
          {
               "jsonrpc": "2.0",
               "method": "res.bank.fields_get",
               "params": [{
                    "kwargs": {
                         "attributes": ["type", "string"]
                    }
               }],
               "id": 0
          }
EOF
     jq 'if has("error") then halt_error else .result end'
echo '</a>'

echo '<a id=create>'
new_record_ids=$(
     (
          curl "$scheme://$domain/RPC2?db=$database" \
               --silent \
               -X POST \
               -H 'Content-Type: application/json' \
               --basic -u "$username:$password" \
               -d @- | \
          jq -c 'if has("error") then halt_error else .result end'
     ) <<EOF
          {
               "jsonrpc": "2.0",
               "method": "res.partner.create",
               "params": [{
                    "args": [{"name": "New Partner"}]
               }],
               "id": 0
          }
EOF
)
echo $new_record_ids
echo '</a>'

echo '<a id=write>'
curl "$scheme://$domain/RPC2?db=$database" \
     --silent \
     -X POST \
     -H 'Content-Type: application/json' \
     --basic -u "$username:$password" \
     -d @- <<EOF |
          {
               "jsonrpc": "2.0",
               "method": "res.partner.write",
               "params": [{
                    "records": $new_record_ids,
                    "args": [{"name": "Newer Partner"}]
               }],
               "id": 0
          }
EOF
     jq 'if has("error") then halt_error else . end' > /dev/null

# get record name after having changed it
curl "$scheme://$domain/RPC2?db=$database" \
     --silent \
     -X POST \
     -H 'Content-Type: application/json' \
     --basic -u "$username:$password" \
     -d @- <<EOF | jq -c 'if has("error") then halt_error else .result end'
          {
               "jsonrpc": "2.0",
               "method": "res.partner.name_get",
               "params": [{
                    "records": $new_record_ids
               }],
               "id": 0
          }
EOF
echo '</a>'

echo '<a id=unlink>'
curl "$scheme://$domain/RPC2?db=$database" \
     --silent \
     -X POST \
     -H 'Content-Type: application/json' \
     --basic -u "$username:$password" \
     -d @- <<EOF |
          {
               "jsonrpc": "2.0",
               "method": "res.partner.unlink",
               "params": [{
                    "records": $new_record_ids
               }],
               "id": 0
          }
EOF
     jq 'if has("error") then halt_error else . end' > /dev/null

# check if the deleted record is still in the database
curl "$scheme://$domain/RPC2?db=$database" \
     --silent \
     -X POST \
     -H 'Content-Type: application/json' \
     --basic -u "$username:$password" \
     -d @- <<EOF |
          {
               "jsonrpc": "2.0",
               "method": "res.partner.exists",
               "params": [{
                    "records": $new_record_ids
               }],
               "id": 0
          }
EOF
     jq 'if has("error") then halt_error else .result end'
echo '</a>'

echo '<a id=ir.model>'
x_custom_model_id=$(
     (
          curl "$scheme://$domain/RPC2?db=$database" \
               --silent \
               -X POST \
               -H 'Content-Type: application/json' \
               --basic -u "$username:$password" \
               -d @- | \
          jq .result[0]
     ) <<EOF
               {
                    "jsonrpc": "2.0",
                    "method": "ir.model.create",
                    "params": [{
                         "args": [{
                                "name": "Custom Model",
                                "model": "x_custom_model",
                                "state": "manual"
                         }]
                    }],
                    "id": 0
               }
EOF
)

# grant the admin CRUD operations
system_group_id=$(
     (
          curl "$scheme://$domain/RPC2?db=$database" \
               --silent \
               -X POST \
               -H 'Content-Type: application/json' \
               --basic -u "$username:$password" \
               -d @- | \
          jq 'if has("error") then halt_error else .result[1] end'
     ) <<EOF
               {
                    "jsonrpc": "2.0",
                    "method": "ir.model.data.check_object_reference",
                    "params": [{
                         "args": ["base", "group_system"]
                    }],
                    "id": 0
               }
EOF
)
curl "$scheme://$domain/RPC2?db=$database" \
     --silent \
     -X POST \
     -H 'Content-Type: application/json' \
     --basic -u "$username:$password" \
     -d @- <<EOF |
          {
               "jsonrpc": "2.0",
               "method": "ir.model.access.create",
               "params": [{
                    "args": [{
                          "name": "access_x_custom_model_admin",
                          "model_id": $x_custom_model_id,
                          "group_id": $system_group_id,
                          "perm_read": true,
                          "perm_write": true,
                          "perm_create": true,
                          "perm_unlink": true
                    }]
               }],
               "id": 0
          }
EOF
     jq 'if has("error") then halt_error else . end' > /dev/null

# get the fields of our newly created model
curl "$scheme://$domain/RPC2?db=$database" \
     --silent \
     -X POST \
     -H 'Content-Type: application/json' \
     --basic -u "$username:$password" \
     -d @- <<EOF |
          {
               "jsonrpc": "2.0",
               "method": "x_custom_model.fields_get",
               "params": [{
                    "kwargs": {
                         "attributes": ["type", "string"]
                    }
               }],
               "id": 0
          }
EOF
     jq 'if has("error") then halt_error else .result end'
echo '</a>'

echo '<a id=ir.model.fields>'
curl "$scheme://$domain/RPC2?db=$database" \
     --silent \
     -X POST \
     -H 'Content-Type: application/json' \
     --basic -u "$username:$password" \
     -d @- <<EOF |
          {
               "jsonrpc": "2.0",
               "method": "ir.model.fields.create",
               "params": [{
                    "args": [{
                           "model_id": $x_custom_model_id,
                           "name": "x_foo",
                           "ttype": "char",
                           "state": "manual"
                    }]
               }],
               "id": 0
          }
EOF
     jq 'if has("error") then halt_error else . end' > /dev/null

# Create a new record and read it
x_record_ids=$(
     (
          curl "$scheme://$domain/RPC2?db=$database" \
               --silent \
               -X POST \
               -H 'Content-Type: application/json' \
               --basic -u "$username:$password" \
               -d @- | \
          jq -c 'if has("error") then halt_error else .result end'
     ) <<EOF
          {
               "jsonrpc": "2.0",
               "method": "x_custom_model.create",
               "params": [{
                    "args": [{"x_foo": "test record"}]
               }],
               "id": 0
          }
EOF
)
curl "$scheme://$domain/RPC2?db=$database" \
     --silent \
     -X POST \
     -H 'Content-Type: application/json' \
     --basic -u "$username:$password" \
     -d @- <<EOF |
          {
               "jsonrpc": "2.0",
               "method": "x_custom_model.read",
               "params": [{
                    "records": $x_record_ids,
                    "kwargs": {
                         "fields": ["x_foo"]
                    }
               }],
               "id": 0
          }
EOF
     jq 'if has("error") then halt_error else .result end'
echo '</a>'
