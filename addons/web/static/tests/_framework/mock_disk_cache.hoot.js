export function mockDiskCacheFactory(name, { fn }) {
    return (requireModule, ...args) => {
        const diskCacheModule = fn(requireModule, ...args);

        const { DiskCache } = diskCacheModule;
        class MockedDiskCache extends DiskCache {
            _execute(callback) {
                return callback();
            }
        }

        return Object.assign(diskCacheModule, {
            DiskCache: MockedDiskCache,
            _OriginalDiskCache: DiskCache,
        });
    };
}
