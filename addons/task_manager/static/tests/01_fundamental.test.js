import { test, expect, mockDate, advanceTime } from "@odoo/hoot";

// Example 1: Basic Assertions
test("addition and string checks", () => {
    const add = (a, b) => a + b;

    expect(add(2, 3)).toBe(5);
    expect(add(-1, 1)).toBe(0);
    expect("Odoo".toLowerCase()).toBe("odoo");
});

// Example 2: Async / Promise Handling
test("async function resolves expected value", async () => {
    const fetchMessage = () => Promise.resolve("Hello, HOOT!");
    const result = await fetchMessage();
    expect(result).toBe("Hello, HOOT!");
});

// Example 3: Mocking Time
test("mockDate and advanceTime example", async () => {
    mockDate("2025-11-06 10:00:00");
    let count = 0;

    setTimeout(() => {
        count++;
    }, 1000);

    await advanceTime(1000);
    expect(count).toBe(1);
});

/**
 * Exercise 1: Even or Odd
 * --------------------------
 * Write a function `isEven(num)` that returns true if `num` is even, false otherwise.
 * Test it with 2 (true), 3 (false), and 0 (true).
 */

/**
 * Exercise 2: Async Sum
 * ------------------------
 * Write an async function `asyncSum(a, b)` that returns the sum of a and b
 * after 200ms delay (use Promise + setTimeout).
 * Test that `await asyncSum(2, 3)` gives 5.
 */

/**
 * Exercise 3: Countdown Timer
 * ------------------------------
 * Write a function `countdown(start)` that decreases a number every 1000ms
 * until it reaches 0.
 * Use `mockDate` + `advanceTime` to test that the countdown completes correctly.
 */
