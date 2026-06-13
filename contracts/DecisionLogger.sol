// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title  PragatiDecisionLogger
 * @notice On-chain immutable audit trail for every AI portfolio decision
 *         made by the PRAGATI.AI engine.
 *
 * Deployment: Sepolia Testnet via Remix IDE (https://remix.ethereum.org)
 *   1. Paste this file into Remix.
 *   2. Compiler → 0.8.20, Optimiser ON (200 runs).
 *   3. Deploy & Run → Environment: Injected Provider - MetaMask (Sepolia).
 *   4. Deploy → confirm transaction in MetaMask.
 *   5. Copy the deployed contract address into your .env file.
 */
contract PragatiDecisionLogger {

    // ── Data Structures ───────────────────────────────────────────────────

    struct Decision {
        uint256 blockIndex;      // PRAGATI local chain block number
        string  decision;        // "APPROVED" | "CAUTION" | "REFUSED"
        string  ipfsCid;         // IPFS CID of full block JSON pinned via Pinata
        bytes32 dataHash;        // keccak256 of the JSON payload (tamper-proof)
        address wallet;          // Wallet address of the investor
        uint256 timestamp;       // Unix timestamp (block.timestamp)
        bool    tradeFrozen;     // Whether the AI froze trading
        uint8   confidenceScore; // 0-100
    }

    // ── State ─────────────────────────────────────────────────────────────

    address public immutable owner;
    Decision[] public decisions;
    mapping(address => uint256[]) private _userDecisionIndexes;

    // ── Events ────────────────────────────────────────────────────────────

    event DecisionLogged(
        uint256 indexed pragatBlockIndex,
        address indexed wallet,
        string  decision,
        string  ipfsCid,
        bytes32 dataHash,
        bool    tradeFrozen,
        uint256 timestamp
    );

    // ── Constructor ───────────────────────────────────────────────────────

    constructor() {
        owner = msg.sender;
    }

    // ── Write Functions ───────────────────────────────────────────────────

    /**
     * @notice Log a new AI decision to the blockchain.
     * @dev    Anyone can log (permissionless audit trail).
     */
    function logDecision(
        uint256 _blockIndex,
        string  calldata _decision,
        string  calldata _ipfsCid,
        bytes32 _dataHash,
        bool    _tradeFrozen,
        uint8   _confidenceScore
    ) external returns (uint256 logIndex) {
        logIndex = decisions.length;

        decisions.push(Decision({
            blockIndex:      _blockIndex,
            decision:        _decision,
            ipfsCid:         _ipfsCid,
            dataHash:        _dataHash,
            wallet:          msg.sender,
            timestamp:       block.timestamp,
            tradeFrozen:     _tradeFrozen,
            confidenceScore: _confidenceScore
        }));

        _userDecisionIndexes[msg.sender].push(logIndex);

        emit DecisionLogged(
            _blockIndex,
            msg.sender,
            _decision,
            _ipfsCid,
            _dataHash,
            _tradeFrozen,
            block.timestamp
        );
    }

    // ── Read Functions ────────────────────────────────────────────────────

    /// @notice Total number of decisions logged.
    function totalDecisions() external view returns (uint256) {
        return decisions.length;
    }

    /// @notice Get a single decision by its log index.
    function getDecision(uint256 logIndex) external view returns (Decision memory) {
        require(logIndex < decisions.length, "Index out of bounds");
        return decisions[logIndex];
    }

    /// @notice All log indexes belonging to a specific wallet.
    function decisionsOf(address wallet) external view returns (uint256[] memory) {
        return _userDecisionIndexes[wallet];
    }

    /// @notice Verify that a stored dataHash matches a provided raw hash.
    function verifyHash(uint256 logIndex, bytes32 expectedHash) external view returns (bool) {
        require(logIndex < decisions.length, "Index out of bounds");
        return decisions[logIndex].dataHash == expectedHash;
    }
}