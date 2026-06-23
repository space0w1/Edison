CREATE TABLE spot_prices (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    price FLOAT NOT NULL,
    volume FLOAT NOT NULL,
    node VARCHAR(255) NOT NULL,
    market VARCHAR(255) NOT NULL
);

CREATE TABLE forward_prices (
    id SERIAL PRIMARY KEY,
    valuation_date TIMESTAMP NOT NULL,
    commodity VARCHAR(255) NOT NULL,
    expiry_date TIMESTAMP NOT NULL,
    price FLOAT NOT NULL
);