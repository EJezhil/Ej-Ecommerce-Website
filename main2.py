import stripe
stripe.api_key = "sk_test_51OPUJESJfMCoVekC64nLMnzBvnkp5EGnaIfQRCHL3CvUhmEOh91XIYZqJCqP43lPv3zU9n24rbBTqnbvBGoIeT6t008VHwI5Dj"

product_id = []
names = []
description = []
images = []
data = stripe.Product.list()

for i in data["data"]:
    product_id.append(i["id"])
    names.append(i["name"])
    description.append(i["description"])
    images.append(i["images"][0])
print(product_id)
print(names)
print(description)
print(images)

price_id = []
prices = []

price = stripe.Price.list()
for i in price["data"]:
    price_id.append(i["id"])
    price_int = i["unit_amount"]
    price_final = str(price_int)[:-2]
    prices.append(price_final)
print(price_id)
print(prices)