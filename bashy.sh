#!/bin/bash

echo "Running post-processing tasks..."
mkdir indivfiles
mv facebook_marketplace* indivfiles

(echo "Please look thorugh the following and give me the best deals, also if I ask about a product give me a link for it, furthermore if I ask about the specifics look up a review of the product on TechPowerUp, give me benchmarks as well."; cat master.txt) | xclip -selection clipboard

echo "Terminating parent Python process..."
pkill -f "python py.py"
