# In this script, since the RPC in betanet is not stable, so we use near-shell instead of RPC interface
# to query the network params.

import requests
import logging

import os
import subprocess
import sys
import time

import json

logging.basicConfig(level = logging.INFO)

# Staking Pool control the staking pool contract.
stakingPoolId = "staking_viboracecata.stakehouse.betanet"

# Master account id control the staked near tokens.
masterAccountId = "lizhongbo3.betanet"

# The node env, be sure it has been exported in system env to be right.
nodeEnv = os.environ.get('NODE_ENV')
# Print out to check the current node env
logging.info(f"######### Current node env: {nodeEnv}")

# Betanet is not stable now, we would better access network from our own node
nodeUrl = "http://45.77.177.210:3030"
shellPostfix = "--node_url " + nodeUrl

rpcUrl = "https://rpc." + nodeEnv + ".near.org"

# If there is ongoing incident, we use this url instead
rpcNodeUrl = nodeUrl

# If we fit our staked tokens it will be this percentage of the estimated seat price
seatPriceFactor = 1.2

# If our current staked tokens is above this threshold we reduce it to the seatPriceFactor amount
upThreshold = 1.3

# Betanet => 10,000, TestNet => 43,200, MainNet => 43,200
epochLength = 10000
slotDuration = 3 * 60 * 60 / epochLength
logging.info(f"########## Slot time: {slotDuration}s")

def getRpcUrl():
    return rpcNodeUrl

def trySeatAdapt():
   ping()
   validatorState = checkValidatorState()
   t2SeatPrice = getT2SeatPrice()
   stakedAmount = getStakedAmount()
   fitStakeVolume(stakedAmount, t2SeatPrice)

# Calculate how many time we should sleep until next epoch.
# Delta 20 seconds to avoid if the calculation is not precise.
def convertSlot2Time(slots):
    time2Sleep = int(slots * slotDuration) - 20
    # Force to sleep at least 6 minutes
    if time2Sleep <= 0:
        time2Sleep = 6 * 60
    return time2Sleep

# Get the t2 information
def getProposals():
    try:
        proposals = subprocess.check_output([f"near proposals {shellPostfix}"], shell=True, env=os.environ,stderr=subprocess.STDOUT).decode('UTF-8')
        return proposals
    except subprocess.CalledProcessError as e:
        logging.error("Get proposals failed", e.returncode, e.output)
        sys.exit()

def reduceStakeVolume(stakedAmount, t2SeatPrice):
    # Unstake additional tokens
    decreaseVolume = int(stakedAmount - (t2SeatPrice * seatPriceFactor))

    if decreaseVolume < 0:
        return

    try:
        subprocess.check_output(
            [f'near call {stakingPoolId} unstake \'{{"amount": "{decreaseVolume}"}}\' --accountId {masterAccountId} {shellPostfix}'],
            env=os.environ,
            shell=True
        ).decode('UTF-8')
    except Exception as exception:
        logging.error("Re-unstaking less near failed!", exception)
        sys.exit()
    logging.info(f"Unstake less near of {decreaseVolume} Succeeded")


def increaseStakeVolume(stakedAmount, t2SeatPrice):
    # Stake more tokens
    increaseVolume = int((t2SeatPrice * seatPriceFactor) - stakedAmount)

    if increaseVolume < 0:
        return

    try:
        subprocess.check_output(
            [f'near call {stakingPoolId} stake \'{{"amount": "{increaseVolume}"}}\' --accountId {masterAccountId} {shellPostfix}'],
            env=os.environ,
            shell=True
        ).decode('UTF-8')
    except Exception as e:
        logging.error("Re-staking more near failed!", e)
        sys.exit()
    logging.info(f"Stake more near of {increaseVolume} Succeeded")

# Query next network params ask time
def getNextQueryTime():
    # Get the current block height.
    rspCurrentHeight = requests.get(getRpcUrl() + "/status").json()
    latestBlockHeight = int(rspCurrentHeight['sync_info']['latest_block_height'])
    logging.info(f"Latest block height is: {latestBlockHeight}")

    # Get the block height of epoch start
    rspEpochHeight = requests.post(getRpcUrl(),
                             json={"jsonrpc": "2.0", "method": "validators", "id": "dontcare", "params": [None]},
                             params='[]',
                             ).json()

    epochStartHeight = int(rspEpochHeight['result']['epoch_start_height'])
    logging.info(f"Epoch start height is: {epochStartHeight}")
    slotDelta = epochStartHeight + epochLength - latestBlockHeight
    if epochStartHeight == 0:
        slotDelta = 10 * 60
    return convertSlot2Time(slotDelta);

def ping():
    try:
        subprocess.check_output(
            [f"near call {stakingPoolId} ping '{{}}' --accountId {masterAccountId} {shellPostfix}"],
            shell=True,
            env=os.environ,
            stderr=subprocess.STDOUT,
        ).decode('UTF-8')
        logging.info(f"Ping of contract {stakingPoolId} succeeded")
    except subprocess.CalledProcessError as e:
        logging.error(f"Ping of contract {stakingPoolId} failed", e.returncode, e.output)
        sys.exit()


def checkValidatorState():
    rspValidators = requests.post(getRpcUrl(),
                             json={"jsonrpc": "2.0", "method": "status", "id": stakingPoolId},
                             params='[]'
                             ).json()
    for validator in rspValidators["result"]["validators"]:
        if validator["account_id"] == stakingPoolId:
            logging.info(f"{stakingPoolId} is validator now")
            return True
        else:
            continue
    logging.error(f"{stakingPoolId} is not validator now")
    return False


def getT2SeatPrice():
    proposals = getProposals()

    # Retrieve the string of seat price
    proposalsSeatPrice = proposals.split("seat price = ")[1].split(")")[0]
    seatYocto = int(proposalsSeatPrice.replace(",", "")) * 10 ** 24
    logging.info(f"Seat price of Proposals: {proposalsSeatPrice}")
    return seatYocto

# If we don't get the staked amount from "near proposals", which means we are not in the list.
# So we should get it from our own account state
def getStakedAmount():
    stakedAmount = getStakedAmountFromT2()
#    if stakedAmount == 0:
#        stakedAmount = getStakedAmountFromAccount()
    return stakedAmount

def findProposedStakeAmount(proposals):
    proposalsLoad = proposals.split(stakingPoolId)[1].split("|")[1]
    if "=>" in proposalsLoad:
        proposedAmount = proposalsLoad.split("=>")[1]
    else:
        proposedAmount = proposalsLoad.split("=>")[0]

    return proposedAmount.replace(",", "").replace(" ", "")

def getStakedAmountFromT2():
    proposals = getProposals()

    try:
        stakedAmount = int(
#            proposals.split(stakingPoolId)[1].split("|")[1].split("=>")[0].replace(",", "").replace(" ", "")
            findProposedStakeAmount(proposals)
        ) * 10 ** 24
    except IndexError:
        stakedAmount = 0
    logging.info(f"{stakingPoolId} has locked {stakedAmount} tokens")
    return stakedAmount

# Want to get the current proposed stake token, but not precise since it can be changed from previous "stake" operation
# Deprecated
def getStakedAmountFromAccount():
    try:
        state = subprocess.check_output(
            [f"near state {stakingPoolId} {shellPostfix}"], shell=True, env=os.environ
        ).decode('UTF-8')

    except Exception as e:
        logging.error(f"Get account {stakingPoolId} state failed:", e)
        sys.exit()

    try:
        lockedAmount = state.split("locked")[1].split(",")[0].replace(": ", "").replace(" ", "").replace("'", "").replace("\x1b[32m", "").replace("\x1b[39m", "")

        logging.info(f"Staked amount of {stakingPoolId} is {lockedAmount}")
        return int(lockedAmount)
    except Exception as e:
        logging.error(f"Get account {stakingPoolId} state failed:", e)
        sys.exit()


def fitStakeVolume(stakedAmount, t2SeatPrice):
    # Reduce staked amount if it is more than the estimated seat price mulptiply a factor
    if stakedAmount > t2SeatPrice * upThreshold:
        reduceStakeVolume(stakedAmount, t2SeatPrice)
    elif stakedAmount < t2SeatPrice:
        increaseStakeVolume(stakedAmount, t2SeatPrice)
    else:
        logging.info("No staked token should be changed")

# According to the epoch start block height and current block height,
# the time this deamon should sleep can be calculated.
def waitNextEpoch():
    waitSeconds = getNextQueryTime()
    logging.info(f"Waiting for {waitSeconds} seconds to start next seat price check")
    time.sleep(waitSeconds)


if __name__ == "__main__":
    logging.info("Start bot to watch and manage stake amount")

    while True:
        logging.info("###################### New round to query network params ############################")
        logging.info("                 ")
        trySeatAdapt()
        logging.info("###################### End of this round ############################")
        logging.info("                 ")
        # Wait until the next epoch
        waitNextEpoch()

