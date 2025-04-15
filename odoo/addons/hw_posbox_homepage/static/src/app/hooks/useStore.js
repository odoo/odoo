/* global owl */

const { useState, useEnv } = owl;

export default function useStore() {
    const env = useEnv();
    return useState(env.store);
}
