export type OrderLine = {
    product_id: number;
    qty: number;
    customer_note: string;
    description: string;
    price_extra: PriceInfo;
};
export type PriceInfo = {
    list_price: number;
    price_with_tax: number;
    price_without_tax: number;
}

export type Product={
    product_id: number;
    price_info: PriceInfo;
    tag: string;
    name: string;
    description_sale: string;
    has_image: boolean;
    attributes: [];
}