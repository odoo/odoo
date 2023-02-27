export type CartItem = {
    product_id: number;
    qty: number;
    customer_note?: string;
};

export type Order = {
    order_id: string;
    access_token: string;
    state: string;
    date: string;
    order_total: string;
    order_items: CartItem[];
};

export type Product = {
    product_id: number;
    name: string;
    list_price: number;
    description_sale: string;
    tag_list: Set<string>;
};
