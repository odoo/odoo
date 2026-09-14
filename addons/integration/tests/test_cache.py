import time
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests import tagged

from odoo.addons.integration.tests.common import APITransportTestCase
from odoo.addons.integration.tools.api_client import get_api_client


@tagged("post_install", "-at_install", "integration")
class TestResponseCache(APITransportTestCase):
    @patch("requests.Session.request")
    def test_cache_miss_first_request(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=200, json_data={"data": "fresh"}
        )

        client = get_api_client(self.env, "test_cache")

        response = client.get("/test/endpoint")

        self.assertSuccessResponse(response)
        self.assertCacheMiss(response)
        self.assertEqual(response["body"]["data"], "fresh")

        self.assertTrue(mock_request.called)

    @patch("requests.Session.request")
    def test_cache_hit_second_request(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=200, json_data={"data": "fresh"}
        )

        client = get_api_client(self.env, "test_cache")

        response1 = client.get("/test/endpoint")
        self.assertCacheMiss(response1)

        mock_request.reset_mock()

        response2 = client.get("/test/endpoint")

        self.assertSuccessResponse(response2)
        self.assertCacheHit(response2)
        self.assertEqual(response2["body"]["data"], "fresh")

        self.assertFalse(mock_request.called)

    def test_cache_expiration(self):
        self.create_cache_entry(
            service=self.service_with_cache,
            url="/test/expired",
            response_body={"data": "expired"},
            ttl=300,
            expired=True,
        )

        cached_response = self.env["integration.response.cache"].get_cached_response(
            endpoint_code="test_cache",
            url="/test/expired",
            company_id=self.env.company.id,
        )

        self.assertIsNone(cached_response)

    def test_cache_valid_entry(self):
        self.create_cache_entry(
            service=self.service_with_cache,
            url="/test/valid",
            response_body={"data": "cached"},
            ttl=300,
            expired=False,
        )

        cached_response = self.env["integration.response.cache"].get_cached_response(
            endpoint_code="test_cache",
            url="/test/valid",
            company_id=self.env.company.id,
        )

        self.assertIsNotNone(cached_response)
        self.assertEqual(cached_response["body"]["data"], "cached")
        self.assertTrue(cached_response["from_cache"])

    def test_cache_hit_count_increment(self):
        cache_entry = self.create_cache_entry(
            service=self.service_with_cache,
            url="/test/hitcount",
            response_body={"data": "test"},
        )

        initial_hit_count = cache_entry.hit_count

        self.env["integration.response.cache"].get_cached_response(
            endpoint_code="test_cache",
            url="/test/hitcount",
            company_id=self.env.company.id,
        )

        cache_entry.invalidate_recordset()
        self.assertEqual(cache_entry.hit_count, initial_hit_count + 1)

    def test_cache_last_accessed_update(self):
        cache_entry = self.create_cache_entry(
            service=self.service_with_cache,
            url="/test/lastaccess",
            response_body={"data": "test"},
        )

        initial_last_accessed = cache_entry.last_accessed

        time.sleep(1.1)

        self.env["integration.response.cache"].get_cached_response(
            endpoint_code="test_cache",
            url="/test/lastaccess",
            company_id=self.env.company.id,
        )

        cache_entry.invalidate_recordset()
        self.assertGreater(cache_entry.last_accessed, initial_last_accessed)

    def test_cache_key_generation(self):
        cache_model = self.env["integration.response.cache"]

        key1 = cache_model._generate_cache_key("test_service", "/endpoint", {"a": 1})
        key2 = cache_model._generate_cache_key("test_service", "/endpoint", {"a": 1})

        self.assertEqual(key1, key2)

        key3 = cache_model._generate_cache_key("test_service", "/endpoint", {"a": 2})
        self.assertNotEqual(key1, key3)

        key4 = cache_model._generate_cache_key("other_service", "/endpoint", {"a": 1})
        self.assertNotEqual(key1, key4)

    def test_cache_invalidation_by_service(self):
        cache1 = self.create_cache_entry(
            service=self.service_with_cache,
            url="/test/1",
        )

        cache2 = self.create_cache_entry(
            service=self.service_stripe,
            url="/test/2",
        )

        count = self.env["integration.response.cache"].invalidate_cache(
            endpoint_code="test_cache"
        )

        self.assertEqual(count, 1)

        self.assertFalse(cache1.exists())

        self.assertTrue(cache2.exists())

    def test_cache_invalidation_by_url_pattern(self):
        cache1 = self.create_cache_entry(
            service=self.service_with_cache,
            url="/api/users/123",
        )

        cache2 = self.create_cache_entry(
            service=self.service_with_cache,
            url="/api/users/456",
        )

        cache3 = self.create_cache_entry(
            service=self.service_with_cache,
            url="/api/products/1",
        )

        count = self.env["integration.response.cache"].invalidate_cache(
            url_pattern="%users%"
        )

        self.assertEqual(count, 2)

        self.assertFalse(cache1.exists())
        self.assertFalse(cache2.exists())

        self.assertTrue(cache3.exists())

    def test_cache_invalidation_by_company(self):
        cache1 = self.create_cache_entry(
            service=self.service_with_cache,
            url="/test/1",
        )
        cache1.company_id = self.env.company

        cache_key_a = self.env["integration.response.cache"]._generate_cache_key(
            "test_cache", "/test/2", None
        )
        self.env["integration.response.cache"].create(
            {
                "cache_key": cache_key_a,
                "endpoint_id": self.service_with_cache.id,
                "company_id": self.company_a.id,
                "request_url": "/test/2",
                "response_body": {"data": "company_a"},
                "date_created": fields.Datetime.now(),
                "date_expiration": fields.Datetime.now() + timedelta(seconds=300),
                "ttl_seconds": 300,
            }
        )

        count = self.env["integration.response.cache"].invalidate_cache(
            company_id=self.env.company.id
        )

        self.assertGreaterEqual(count, 1)

    def test_cache_cleanup_cron(self):
        expired1 = self.create_cache_entry(
            url="/test/expired1",
            ttl=300,
            expired=True,
        )

        expired2 = self.create_cache_entry(
            url="/test/expired2",
            ttl=300,
            expired=True,
        )

        valid = self.create_cache_entry(
            url="/test/valid",
            ttl=300,
            expired=False,
        )

        self.env["integration.response.cache"]._gc_expired_cache()

        self.assertFalse(expired1.exists())
        self.assertFalse(expired2.exists())

        self.assertTrue(valid.exists())

    def test_cache_lru_cleanup(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "integration.max_cache_entries", "5"
        )

        caches = []
        for i in range(10):
            cache = self.create_cache_entry(
                url=f"/test/{i}",
                response_body={"index": i},
            )
            caches.append(cache)

        for i, cache in enumerate(caches):
            cache.write({"hit_count": i})

        self.env["integration.response.cache"]._gc_least_used_cache()

        remaining = self.env["integration.response.cache"].search([])

        self.assertLessEqual(len(remaining), 5)

        if len(remaining) > 0:
            min_hit_count = min(remaining.mapped("hit_count"))
            self.assertGreaterEqual(min_hit_count, 5)

    @patch("requests.Session.request")
    def test_cache_disabled_service(self, mock_request):
        mock_request.return_value = self.create_mock_response(
            status_code=200, json_data={"data": "test"}
        )

        client = get_api_client(self.env, "test_stripe")

        response1 = client.get("/test")
        response2 = client.get("/test")

        self.assertCacheMiss(response1)
        self.assertCacheMiss(response2)

        self.assertEqual(mock_request.call_count, 2)

    def test_cache_params_hash(self):
        cache_model = self.env["integration.response.cache"]

        params1 = {"b": 2, "a": 1}
        params2 = {"a": 1, "b": 2}

        hash1 = cache_model._generate_params_hash(params1)
        hash2 = cache_model._generate_params_hash(params2)

        self.assertEqual(hash1, hash2)

        params3 = {"a": 1, "b": 3}
        hash3 = cache_model._generate_params_hash(params3)

        self.assertNotEqual(hash1, hash3)

    def test_concurrent_cache_writes(self):
        cache_model = self.env["integration.response.cache"]

        endpoint_code = "test_concurrent_cache"
        url = "/test/concurrent"
        cache_key = cache_model._generate_cache_key(endpoint_code, url, None)
        company_id = self.env.company.id

        with self.env.registry.cursor() as setup_cr:
            setup_env = self.env(cr=setup_cr)
            seeded_service = setup_env["integration.service"].create(
                {
                    "name": "Concurrent Cache Test",
                    "code": endpoint_code,
                    "category": "other",
                    "endpoint_url": "https://api.concurrent.com",
                    "environment": "production",
                    "cache_enabled": True,
                    "cache_ttl": 300,
                },
            )
            seeded_service_id = seeded_service.id
            setup_cr.commit()

        def _cleanup():
            with self.env.registry.cursor() as cleanup_cr:
                cleanup_cr.execute(
                    "DELETE FROM integration_response_cache "
                    "WHERE cache_key = %s AND company_id = %s",
                    (cache_key, company_id),
                )
                cleanup_cr.execute(
                    "DELETE FROM integration_service WHERE id = %s",
                    (seeded_service_id,),
                )
                cleanup_cr.commit()

        self.addCleanup(_cleanup)

        errors = []
        successful_writes = []

        for thread_id in range(10):
            try:
                with self.env.registry.cursor() as new_cr:
                    new_env = self.env(cr=new_cr)
                    new_env["integration.response.cache"].set_cached_response(
                        endpoint_code=endpoint_code,
                        url=url,
                        response={
                            "body": {
                                "thread": thread_id,
                                "data": f"test_{thread_id}",
                            },
                            "headers": {"Content-Type": "application/json"},
                            "status_code": 200,
                        },
                        ttl=300,
                        params=None,
                        company_id=company_id,
                    )
                    new_cr.commit()
                    successful_writes.append(thread_id)
            except Exception as e:  # pylint: disable=broad-except
                errors.append((thread_id, repr(e)))

        self.assertEqual(
            len(errors),
            0,
            f"Concurrent cache writes failed with errors: {errors}",
        )
        self.assertGreater(
            len(successful_writes),
            0,
            "No successful cache writes from concurrent transactions",
        )

        with self.env.registry.cursor() as verify_cr:
            verify_cr.execute(
                "SELECT COUNT(*) FROM integration_response_cache "
                "WHERE cache_key = %s AND company_id = %s",
                (cache_key, company_id),
            )
            (count,) = verify_cr.fetchone()
        self.assertEqual(
            count,
            1,
            f"Expected exactly 1 cache entry, found {count}",
        )

        with self.env.registry.cursor() as verify_cr:
            verify_cr.execute(
                """
                SELECT s.code, c.request_url
                FROM integration_response_cache c
                JOIN integration_service s ON s.id = c.endpoint_id
                WHERE c.cache_key = %s AND c.company_id = %s
                """,
                (cache_key, company_id),
            )
            row = verify_cr.fetchone()
        self.assertIsNotNone(row, "Cache entry disappeared between checks")
        self.assertEqual(row[0], endpoint_code)
        self.assertEqual(row[1], url)
