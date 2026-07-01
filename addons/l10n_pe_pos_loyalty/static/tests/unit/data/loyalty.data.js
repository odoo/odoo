import { LoyaltyCard } from "@pos_loyalty/../tests/unit/data/loyalty_card.data";
import { LoyaltyProgram } from "@pos_loyalty/../tests/unit/data/loyalty_program.data";
import { LoyaltyReward } from "@pos_loyalty/../tests/unit/data/loyalty_reward.data";

LoyaltyReward._records = [
    ...LoyaltyReward._records,
    {
        id: 50,
        description: "eWallet Pay",
        program_id: 2,
        reward_type: "discount",
        required_points: 1,
        clear_wallet: false,
        currency_id: 1,
        discount: 1,
        discount_mode: "per_point",
        discount_applicability: "order",
        all_discount_product_ids: [],
        is_global_discount: false,
        discount_max_amount: 0,
        discount_line_product_id: 5,
        reward_product_id: false,
        multi_product: false,
        reward_product_ids: [],
        reward_product_qty: 1,
        reward_product_uom_id: false,
        reward_product_domain: "[]",
    },
];

LoyaltyProgram._records = LoyaltyProgram._records.map((record) =>
    record.id === 2 ? { ...record, reward_ids: [50] } : record
);

// Tax-included top-up amount from the reported bug (33.33 with 18% IGV).
LoyaltyCard._records = LoyaltyCard._records.map((record) =>
    record.id === 2 ? { ...record, points: 33.33 } : record
);
