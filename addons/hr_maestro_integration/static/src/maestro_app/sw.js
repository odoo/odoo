const MAESTRO_CACHE = 'maestro-app-v1'
const APP_SHELL = ['/maestro/app', '/maestro/app/manifest.json']

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(MAESTRO_CACHE).then((cache) => cache.addAll(APP_SHELL))
  )
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys.filter((key) => key !== MAESTRO_CACHE).map((key) => caches.delete(key))
    ))
  )
  self.clients.claim()
})

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const copy = response.clone()
        caches.open(MAESTRO_CACHE).then((cache) => cache.put(event.request, copy))
        return response
      })
      .catch(() => caches.match(event.request).then((cached) => cached || caches.match('/maestro/app')))
  )
})

self.addEventListener('push', (event) => {
  let data = {}
  try { data = event.data ? event.data.json() : {} } catch (e) { data = {title: 'Maestro', body: event.data ? event.data.text() : ''} }
  const title = data.title || 'Maestro Intelligence'
  const options = {
    body: data.body || '',
    icon: '/hr_maestro_integration/static/src/maestro_app/icons/icon-192.png',
    badge: '/hr_maestro_integration/static/src/maestro_app/icons/icon-192.png',
    data: {url: data.url || '/maestro/app'},
  }
  event.waitUntil(self.registration.showNotification(title, options))
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const url = (event.notification.data && event.notification.data.url) || '/maestro/app'
  event.waitUntil(
    self.clients.matchAll({type: 'window'}).then((clients) => {
      for (const client of clients) {
        if (client.url.includes('/maestro/app') && 'focus' in client) return client.focus()
      }
      return self.clients.openWindow(url)
    })
  )
})
