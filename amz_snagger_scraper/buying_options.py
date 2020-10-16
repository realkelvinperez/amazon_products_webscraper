def get_sold_by():
    sold_by_node = response.css(".olpSellerName a::text").get()
    sold_by = clean_text(sold_by_node)
    return sold_by


def get_price():
    price_node = response.css(".olpOffer .olpOfferPrice::text").get()
    price_pattern = re.compile(r"\$(.*)")
    price_text = price_pattern.search(price_node)
    price = int(clean_text(price_text[0]))
    return price


def get_sellers():
    all_sellers_node = response.css(".olpOffer").get()
    sellers = len(all_sellers_node)
    return sellers